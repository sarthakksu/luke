In this code, you can experiment with the task of entity typing.  
Currently, we support the following datasets.


#####  English 
* [Open Entity](https://www.aclweb.org/anthology/P18-1009/)

# Download datasets
```bash
cd data
wget http://nlp.cs.washington.edu/entity_type/data/release.tar.gz
tar -zxvf ultrafine_acl18.tar.gz
```

We only use the manually annotated data under `release/crowd` for training and evaluation.

# Training
We configure some parameters through environmental variables.
```bash
export SEED=0;
export TRAIN_DATA_PATH="data/release/crowd/train.json";
export VALIDATION_DATA_PATH="data/release/crowd/dev.json";

# train LUKE
export TRANSFORMERS_MODEL_NAME="studio-ousia/luke-base";
poetry run allennlp train examples/entity_typing/configs/transformers_luke.jsonnet -s results/entity_typing/luke-base --include-package examples -o '{"trainer": {"cuda_device": 0}}'

# you can also fine-tune models from the BERT family
export TRANSFORMERS_MODEL_NAME="roberta-base";
poetry run allennlp train examples/entity_typing/configs/transformers.jsonnet  -s results/entity_typing/roberta-base --include-package examples
```

# Evaluation
```bash
poetry run allennlp evaluate RESULT_SAVE_DIR INPUT_FILE --include-package examples --output-file OUTPUT_FILE 

# example for LUKE
poetry run allennlp evaluate results/entity_typing/luke-base data/release/crowd/test.json --include-package examples --output-file results/entity_typing/luke-base/metrics_test.json --cuda 0
```

# Make Prediction
```bash
poetry run allennlp predict RESULT_SAVE_DIR INPUT_FILE --use-dataset-reader --include-package examples --cuda-device CUDA_DEVICE --output-file OUTPUT_FILE

# example for LUKE
poetry run allennlp predict results/entity_typing/luke-base data/release/crowd/dev.json --use-dataset-reader --include-package examples --cuda-device 0 --output-file results/entity_typing/luke-base/prediction.json
```

