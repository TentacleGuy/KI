from transformers import Trainer, TrainingArguments, GPT2LMHeadModel, GPT2Tokenizer, TrainerCallback
from utils import load_json
from constants import TRAININGDATA_FILE

# Custom Callback für das Logging
class LogCallback(TrainerCallback):
    def __init__(self, log_callback, log_text_widget):
        self.log_callback = log_callback
        self.log_text_widget = log_text_widget  # Das Log-Textfeld übergeben

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs is not None:
            # Log-Meldungen in einen lesbaren Text umwandeln
            log_message = ", ".join([f"{key}: {value}" for key, value in logs.items()])
            # Log-Nachricht mit dem zugehörigen Text-Widget an die GUI übergeben
            self.log_callback(self.log_text_widget, log_message)


# Initialisiere das Modell und den Trainer
def initialize_trainer(model_name, epochs, learning_rate, batch_size, log_callback, log_text_widget):
    # Lade das GPT-2 Modell und den Tokenizer
    model = GPT2LMHeadModel.from_pretrained(model_name)
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)

    # Setze den `pad_token` auf das `eos_token`
    tokenizer.pad_token = tokenizer.eos_token

    # Lade deinen eigenen Datensatz (trainingdata.json)
    dataset = load_json(TRAININGDATA_FILE)

    # Konvertiere die Daten in ein Format, das der Trainer verarbeiten kann
    texts = [data['lyrics'] for data in dataset]

    # Tokenisierung
    def tokenize_function(examples):
        tokens = tokenizer(examples, padding="max_length", truncation=True, max_length=128)
        tokens["labels"] = tokens["input_ids"].copy()  # Labels als Kopie der input_ids hinzufügen
        return tokens

    tokenized_texts = [tokenize_function(text) for text in texts]

    # Benutzerdefiniertes Dataset
    class CustomDataset:
        def __init__(self, tokenized_texts):
            self.tokenized_texts = tokenized_texts

        def __len__(self):
            return len(self.tokenized_texts)

        def __getitem__(self, idx):
            return self.tokenized_texts[idx]

    custom_dataset = CustomDataset(tokenized_texts)

    # Trainingsargumente
    training_args = TrainingArguments(
        output_dir="./results",
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=learning_rate,
        logging_dir="./logs",
        logging_steps=10,
        report_to=None  # Verhindert das Senden von Logs an externe Dienste wie WandB
    )

    # Trainer initialisieren mit dem LogCallback
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=custom_dataset,
        tokenizer=tokenizer,
        callbacks=[LogCallback(log_callback, log_text_widget)]  # Hier wird der Callback mit dem richtigen Textfeld hinzugefügt
    )

    return trainer, training_args



