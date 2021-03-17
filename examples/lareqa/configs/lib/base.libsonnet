local seed = std.parseInt(std.extVar("SEED"));
local batch_size = std.parseInt(std.extVar("BATCH_SIZE"));
local accumulation_steps = std.parseInt(std.extVar("ACCUMULATION_STEPS"));
local train_data_path = std.extVar("TRAINE_DATA_PATH");
local validation_data_path = std.extVar("VALIDATION_DATA_PATH");


local total_steps = std.parseInt(std.extVar("TOTAL_STEPS"));

{
    "train_data_path": train_data_path,
    "validation_data_path": validation_data_path,
    "data_loader": {
        "batch_size": batch_size, "shuffle": true
    },
    "trainer": {
        "num_epochs": 100,
        "patience": 5,
        "cuda_device": -1,
        "grad_norm": 0.25
        ,
        "num_gradient_accumulation_steps": accumulation_steps,
        "checkpointer": {
            "num_serialized_models_to_keep": 0
        },
        "validation_metric": "-loss",
        "optimizer": {
            "type": "adamw",
            "lr": 1e-5
        },
        "learning_rate_scheduler": {
            "type": "polynomial_decay",
            "warmup_steps": total_steps / 10,
            "num_epochs": 10,
            "num_steps_per_epoch": total_steps / 10,
        },
    },
    "random_seed": seed,
    "numpy_seed": seed,
    "pytorch_seed": seed
}
