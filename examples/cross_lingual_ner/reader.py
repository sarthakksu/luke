from typing import Dict, List
import itertools
import math
import numpy as np
from allennlp.data import Tokenizer, DatasetReader, TokenIndexer, Instance, Token
from allennlp.data.tokenizers import PretrainedTransformerTokenizer
from allennlp.data.fields import TextField, ArrayField, MetadataField, LabelField, ListField

NON_ENTITY = "O"


def parse_conll_ner_data(input_file: str, encoding: str = "utf-8"):

    words: List[str] = []
    labels: List[str] = []
    sentence_boundaries: List[int] = [0]

    try:
        with open(input_file, "r", encoding=encoding) as f:
            for line in f:
                line = line.rstrip()
                if line.startswith("-DOCSTART"):
                    if words:
                        assert sentence_boundaries[0] == 0
                        assert sentence_boundaries[-1] == len(words)
                        yield words, labels, sentence_boundaries
                        words = []
                        labels = []
                        sentence_boundaries = [0]
                    continue

                if not line:
                    if len(words) != sentence_boundaries[-1]:
                        sentence_boundaries.append(len(words))
                else:
                    parts = line.split(" ")
                    words.append(parts[0])
                    labels.append(parts[-1])

        if words:
            yield words, labels, sentence_boundaries
    except UnicodeDecodeError as e:
        raise Exception("The specified encoding seems wrong. Try either ISO-8859-1 or utf-8.") from e


@DatasetReader.register("conll_exhaustive")
class ConllExhaustiveReader(DatasetReader):
    def __init__(
        self,
        token_indexers: Dict[str, TokenIndexer],
        tokenizer: Tokenizer = None,
        max_sequence_length: int = 512,
        max_entity_length: int = 128,
        max_mention_length: int = 16,
        encoding: str = "utf-8",
        use_entity_feature: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.tokenizer = tokenizer
        self.token_indexers = token_indexers

        self.max_num_subwords = max_sequence_length - 2  # take the number of Special tokens into account
        self.max_entity_length = max_entity_length
        self.max_mention_length = max_mention_length

        self.encoding = encoding
        self.use_entity_feature = use_entity_feature

    def data_to_instance(self, words: List[str], labels: List[str], sentence_boundaries: List[int], doc_index: str):
        if self.tokenizer is None:
            tokens = [[Token(w)] for w in words]
        else:
            tokens = [self.tokenizer.tokenize(w) for w in words]
        subwords = [sw for token in tokens for sw in token]

        subword2token = list(itertools.chain(*[[i] * len(token) for i, token in enumerate(tokens)]))
        token2subword = [0] + list(itertools.accumulate(len(token) for token in tokens))
        subword_start_positions = frozenset(token2subword)
        subword_sentence_boundaries = [sum(len(token) for token in tokens[:p]) for p in sentence_boundaries]

        # get the span indices of subwords for entities
        entity_labels = {}
        start = None
        cur_type = None
        for n, label in enumerate(labels):
            if label == "O" or n in sentence_boundaries:
                if start is not None:
                    entity_labels[(token2subword[start], token2subword[n])] = cur_type
                    start = None
                    cur_type = None

            if label.startswith("B"):
                if start is not None:
                    entity_labels[(token2subword[start], token2subword[n])] = cur_type
                start = n
                cur_type = label[2:]

            elif label.startswith("I"):
                if start is None:
                    start = n
                    cur_type = label[2:]
                elif cur_type != label[2:]:
                    entity_labels[(token2subword[start], token2subword[n])] = cur_type
                    start = n
                    cur_type = label[2:]

        if start is not None:
            entity_labels[(token2subword[start], len(subwords))] = cur_type

        # split data according to sentence boundaries
        for n in range(len(subword_sentence_boundaries) - 1):
            # process (sub) words
            doc_sent_start, doc_sent_end = subword_sentence_boundaries[n : n + 2]

            left_length = doc_sent_start
            right_length = len(subwords) - doc_sent_end
            sentence_length = doc_sent_end - doc_sent_start
            half_context_length = int((self.max_num_subwords - sentence_length) / 2)

            if left_length < right_length:
                left_context_length = min(left_length, half_context_length)
                right_context_length = min(right_length, self.max_num_subwords - left_context_length - sentence_length)
            else:
                right_context_length = min(right_length, half_context_length)
                left_context_length = min(left_length, self.max_num_subwords - right_context_length - sentence_length)

            doc_offset = doc_sent_start - left_context_length
            word_ids = subwords[doc_offset : doc_sent_end + right_context_length]

            if isinstance(self.tokenizer, PretrainedTransformerTokenizer):
                word_ids = self.tokenizer.add_special_tokens(word_ids)

            # process entities
            entity_start_positions = []
            entity_end_positions = []
            entity_ids = []
            entity_position_ids = []
            original_entity_spans = []
            labels = []

            for entity_start in range(left_context_length, left_context_length + sentence_length):
                doc_entity_start = entity_start + doc_offset
                if doc_entity_start not in subword_start_positions:
                    continue
                for entity_end in range(entity_start + 1, left_context_length + sentence_length + 1):
                    doc_entity_end = entity_end + doc_offset
                    if doc_entity_end not in subword_start_positions:
                        continue

                    if entity_end - entity_start > self.max_mention_length:
                        continue

                    entity_start_positions.append(entity_start + 1)
                    entity_end_positions.append(entity_end)
                    entity_ids.append(1)

                    position_ids = list(range(entity_start + 1, entity_end + 1))
                    position_ids += [-1] * (self.max_mention_length - entity_end + entity_start)
                    entity_position_ids.append(position_ids)

                    original_entity_spans.append(
                        (subword2token[doc_entity_start], subword2token[doc_entity_end - 1] + 1)
                    )

                    labels.append(entity_labels.get((doc_entity_start, doc_entity_end), NON_ENTITY))
                    entity_labels.pop((doc_entity_start, doc_entity_end), None)

            # split instances
            split_size = math.ceil(len(entity_ids) / self.max_entity_length)
            for i in range(split_size):
                entity_size = math.ceil(len(entity_ids) / split_size)
                start = i * entity_size
                end = start + entity_size
                fields = {
                    "word_ids": TextField(word_ids, token_indexers=self.token_indexers),
                    "entity_start_positions": ArrayField(np.array(entity_start_positions[start:end])),
                    "entity_end_positions": ArrayField(np.array(entity_end_positions[start:end])),
                    "original_entity_spans": ArrayField(np.array(original_entity_spans[start:end]), padding_value=-1),
                    "labels": ListField([LabelField(l) for l in labels[start:end]]),
                    "doc_id": MetadataField(doc_index),
                }

                if self.use_entity_feature:
                    fields.update(
                        {
                            "entity_ids": ArrayField(np.array(entity_ids[start:end])),
                            "entity_position_ids": ArrayField(np.array(entity_position_ids[start:end])),
                        }
                    )

                yield Instance(fields)

    def _read(self, file_path: str):
        for i, (words, labels, sentence_boundaries) in enumerate(
            parse_conll_ner_data(file_path, encoding=self.encoding)
        ):
            yield from self.data_to_instance(words, labels, sentence_boundaries, f"doc{i}")
