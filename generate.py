import threading
import time
from tkinter import messagebox, Toplevel, Label, Text, ttk
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch

def start_lyrics_generation(app):
    model = app.model_var.get()
    title = app.title_entry.get()
    style = app.style_entry.get()
    prompt = app.prompt_entry.get("1.0", "end-1c")

    app.log(app.log_text, f"Generating lyrics with:\nModel: {model}\nTitle: {title}\nStyle: {style}\nPrompt: {prompt}\n")

    threading.Thread(target=generate_lyrics_thread, args=(app, model, title, style, prompt)).start()

def generate_lyrics_thread(app, model, title, style, prompt):
    try:
        app.after(0, lambda: app.log(app.log_text, "Starting lyrics generation...\n"))
        
        model_path = f"results/{model}"
        model = GPT2LMHeadModel.from_pretrained(model_path)
        tokenizer = GPT2Tokenizer.from_pretrained(model_path)
        
        full_prompt = f"Title: {title}\nStyle: {style}\nPrompt: {prompt}\n\nLyrics:\n"
        input_ids = tokenizer.encode(full_prompt, return_tensors='pt')
        
        attention_mask = torch.ones_like(input_ids)
        pad_token_id = tokenizer.eos_token_id
        
        output = model.generate(
            input_ids,
            attention_mask=attention_mask,
            max_length=200,
            num_return_sequences=1,
            no_repeat_ngram_size=2,
            do_sample=True,
            temperature=0.7,
            pad_token_id=pad_token_id
        )
        
        generated_lyrics = tokenizer.decode(output[0], skip_special_tokens=True)
        
        app.after(0, lambda: app.log(app.log_text, "Lyrics generated successfully!\n"))
        app.after(0, lambda: show_lyrics_window(app, title, style, generated_lyrics))
    except Exception as e:
        app.after(0, lambda: app.log(app.log_text, f"Error during lyrics generation: {str(e)}\n"))

def show_lyrics_window(app, title, style, lyrics):
    lyrics_window = Toplevel(app)
    lyrics_window.title("Generated Lyrics")

    Label(lyrics_window, text=f"Title: {title}").pack(pady=5)
    Label(lyrics_window, text=f"Style: {style}").pack(pady=5)

    lyrics_text = Text(lyrics_window, wrap="word", height=20, width=50)
    lyrics_text.pack(padx=10, pady=10)
    lyrics_text.insert("end", lyrics)

    copy_button = ttk.Button(lyrics_window, text="Copy to Clipboard", command=lambda: copy_to_clipboard(app, lyrics))
    copy_button.pack(pady=10)

def copy_to_clipboard(app, text):
    app.clipboard_clear()
    app.clipboard_append(text)
    messagebox.showinfo("Info", "Lyrics copied to clipboard!")
