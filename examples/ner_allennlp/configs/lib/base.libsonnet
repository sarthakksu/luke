local transformers_model_name = std.extVar("TRANSFORMERS_MODEL_NAME");
local train_data_path = std.extVar("TRAIN_DATA_PATH");
local validation_data_path = std.extVar("VALIDATION_DATA_PATH");

local lr = 1e-5;
local batch_size = 4;
local accumulation_steps = 2;
local num_epochs = 5;
local num_steps_per_epoch = 22128;

local base = import "lib/base.libsonnet";

local tokenizer = {"type": "pretrained_transformer", "model_name": transformers_model_name,
                    "add_special_tokens": false,  "tokenizer_kwargs": {"add_prefix_space": true}};
local token_indexers = {
            "tokens": {"type": "pretrained_transformer", "model_name": transformers_model_name}
    };


{
    "dataset_reader": {
        "type": "conll_exhaustive",
        "tokenizer": tokenizer,
        "token_indexers": token_indexers,
        "encoding": "utf-8",
    },
    "train_data_path": train_data_path,
    "validation_data_path": validation_data_path,
    "trainer": {
        "cuda_device": -1,
        "grad_norm": 5,
        "num_epochs": num_epochs,
        "checkpointer": {
            "keep_most_recent_by_count": 0
        },
        "optimizer": {
            "type": "adamw",
            "lr": lr,
            "weight_decay": 0.01,
            "parameter_groups": [
                [
                    [
                        "bias",
                        "LayerNorm.weight",
                    ],
                    {
                        "weight_decay": 0
                    }
                ]
            ],
        },
        "learning_rate_scheduler": {
            "type": "linear_with_warmup",
            "warmup_steps": std.floor(num_steps_per_epoch * num_epochs / 10)
        },
        "num_gradient_accumulation_steps": accumulation_steps,
        "patience": 3,
        "validation_metric": "+f1"
    },
    "data_loader": {"batch_size": batch_size, "shuffle": true}
}