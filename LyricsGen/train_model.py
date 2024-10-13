def train_suno_model(log_callback):
    """Trainiert ein Modell basierend auf den gesammelten Songdaten."""
    log_callback("Starte KI-Training...")

    # Lade dein Dataset
    dataset = load_dataset('json', data_files=f'{SONGS_DIR}/*.json')

    # Dataset in train und test aufteilen (80% train, 20% test)
    split_dataset = dataset["train"].train_test_split(test_size=0.2)

    # Tokenizer und Modell laden
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token

    model = GPT2LMHeadModel.from_pretrained("gpt2")

    # Dataset tokenisieren
    def tokenize_function(examples):
        return tokenizer(examples["lyrics"], padding="max_length", truncation=True, max_length=512)

    tokenized_datasets = split_dataset.map(tokenize_function, batched=True)

    # Trainingseinstellungen
    training_args = TrainingArguments(
        output_dir="./results",
        evaluation_strategy="epoch",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        logging_dir="./logs",
    )

    # Trainer initialisieren
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
    )

    log_callback("Training wird gestartet...")
    trainer.train()
    log_callback("Training abgeschlossen!")
