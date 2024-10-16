import torch
from torch.utils.data import Dataset, DataLoader
from transformers import GPT2LMHeadModel, GPT2Tokenizer, AdamW, get_linear_schedule_with_warmup
from utils import load_json
from constants import *
import datetime
from tqdm import tqdm
import matplotlib.pyplot as plt
import GPUtil
import psutil
import threading
from torch.cuda.amp import autocast, GradScaler
from torchvision.utils import make_grid
from torchsummary import summary
from sklearn.metrics import confusion_matrix
import seaborn as sns
import tkinter as tk
import matplotlib
from torch.optim import AdamW
import os
import re

matplotlib.use('Agg')

class LyricsDataset(Dataset):
    def __init__(self, tokenizer, data, max_length):
        self.tokenizer = tokenizer
        self.data = data
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        lyrics = self.data[idx]['lyrics']
        encoding = self.tokenizer(lyrics, return_tensors='pt', max_length=self.max_length, 
                                  truncation=True, padding='max_length')
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten()
        }

def initialize_trainer(model, epochs, learning_rate, batch_size, max_length, warmup_steps, 
                       weight_decay, gradient_accumulation_steps):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model = model.to(device)
    tokenizer = GPT2Tokenizer.from_pretrained(model.config._name_or_path)
    tokenizer.pad_token = tokenizer.eos_token

    dataset = load_json(TRAININGDATA_FILE)
    train_dataset = LyricsDataset(tokenizer, dataset, max_length)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    optimizer = AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, 
                                                num_training_steps=len(train_loader) * epochs)

    return model, train_loader, optimizer, scheduler, device, tokenizer

def train(model, train_loader, optimizer, scheduler, device, epochs, 
          gradient_accumulation_steps, log_training_message, log_text_widget):
    model.train()
    losses = []
    for epoch in range(epochs):
        epoch_loss = 0
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}")
        for batch_idx, batch in enumerate(progress_bar):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            
            outputs = model(input_ids, attention_mask=attention_mask, labels=input_ids)
            loss = outputs.loss
            loss = loss / gradient_accumulation_steps
            loss.backward()

            if (batch_idx + 1) % gradient_accumulation_steps == 0:
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            epoch_loss += loss.item()
            progress_bar.set_postfix({'loss': loss.item()})
            
            log_training_message(log_text_widget, f"Epoch {epoch+1}, Batch Loss: {loss.item():.4f}")
        
        avg_loss = epoch_loss / len(train_loader)
        losses.append(avg_loss)
        log_training_message(log_text_widget, f"Epoch {epoch+1} completed. Average Loss: {avg_loss:.4f}")
    
    return losses

def plot_loss(losses):
    plt.figure(figsize=(10, 5))
    plt.plot(losses)
    plt.title('Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.savefig('training_loss.png')
    plt.close()

def monitor_resources():
    gpu = GPUtil.getGPUs()[0]
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    gpu_utilization = gpu.load * 100
    gpu_memory = gpu.memoryUtil * 100
    return f"CPU: {cpu_percent}%, RAM: {memory_percent}%, GPU: {gpu_utilization:.2f}%, GPU Memory: {gpu_memory:.2f}%"

def save_model(model, optimizer, epoch, loss, path):
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'loss': loss,
    }, path)

def save_trained_model(model, tokenizer, model_name, input_values):
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{current_time},{model_name},epochs-{input_values['epochs']},learningrate-{input_values['learning_rate']},batchsize-{input_values['batch_size']},maxlength-{input_values['max_length']},warmupsteps-{input_values['warmup_steps']},weightdecay-{input_values['weight_decay']},gradaccumsteps-{input_values['gradient_accumulation_steps']}"
    
    folder_name = re.sub(r'[^\w\-_\.,]', '_', folder_name)
    if len(folder_name) > 255:
        folder_name = folder_name[:255]
    
    save_directory = os.path.join("results", folder_name)
    os.makedirs(save_directory, exist_ok=True)
    model.save_pretrained(save_directory)
    tokenizer.save_pretrained(save_directory)
    print(f"Modell wurde gespeichert in: {save_directory}")

def load_model(model, optimizer, path):
    checkpoint = torch.load(path)
    model.load_state_dict(checkpoint['model_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    epoch = checkpoint['epoch']
    loss = checkpoint['loss']
    return model, optimizer, epoch, loss

class TrainingManager:
    def __init__(self, log_training_message, root=None):
            self.log_training_message = log_training_message
            self.root = root
            self.stop_training_flag = False
            self.training_thread = None

    def start_training(self, model_name, log_text_widget, progress_var, status_var, resource_var, loss_plot, **hyperparams):
        self.stop_training_flag = False
        self.training_thread = threading.Thread(target=self.run_training, args=(model_name, log_text_widget, progress_var, status_var, resource_var, loss_plot), kwargs=hyperparams)
        self.training_thread.start()

    def stop_training(self):
        self.stop_training_flag = True

    def run_training(self, model_name, log_text_widget, progress_var, status_var, resource_var, loss_plot, **hyperparams):
        model, train_loader, optimizer, scheduler, device, tokenizer = initialize_trainer(model_name, **hyperparams)
        
        for epoch in range(hyperparams['epochs']):
            if self.stop_training_flag:
                break
            losses = train(model, train_loader, optimizer, scheduler, device, 1, 
                    hyperparams['gradient_accumulation_steps'], self.log_training_message, log_text_widget)
    
            # Update progress
            progress_var.set((epoch + 1) / hyperparams['epochs'] * 100)
            
            # Update loss plot
            plot_loss(losses)
            self.update_loss_plot(loss_plot, 'training_loss.png')

            # Update resource usage
            resource_var.set(monitor_resources())

        save_trained_model(model, tokenizer, str(model_name), hyperparams)
        status_var.set("Training completed")
    
    def update_loss_plot(self, loss_plot, image_path):
        if hasattr(loss_plot, 'after'):
            loss_plot.after(0, lambda: loss_plot.config(image=tk.PhotoImage(file=image_path)))
            
training_manager = TrainingManager(log_training_message=None)

def log_training_message(log_training_message):
    training_manager.log_training_message = log_training_message

def plot_confusion_matrix(y_true, y_pred, classes):
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=classes, yticklabels=classes)
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig('confusion_matrix.png')
    plt.close()

def visualize_model_architecture(model):
    summary(model, input_size=(1, 512))  # Adjust input size as needed

def plot_learning_rate(scheduler, epochs):
    lrs = []
    for _ in range(epochs):
        lrs.append(scheduler.get_last_lr()[0])
        scheduler.step()
    
    plt.figure(figsize=(10, 5))
    plt.plot(lrs)
    plt.title('Learning Rate Schedule')
    plt.xlabel('Epoch')
    plt.ylabel('Learning Rate')
    plt.savefig('learning_rate_schedule.png')
    plt.close()

def plot_gradient_flow(named_parameters):
    ave_grads = []
    layers = []
    for n, p in named_parameters:
        if(p.requires_grad) and ("bias" not in n):
            layers.append(n)
            ave_grads.append(p.grad.abs().mean().item())
    plt.figure(figsize=(10, 8))
    plt.bar(range(len(ave_grads)), ave_grads, align="center")
    plt.xticks(range(len(ave_grads)), layers, rotation="vertical")
    plt.xlabel("Layers")
    plt.ylabel("Average gradient")
    plt.title("Gradient flow")
    plt.tight_layout()
    plt.savefig('gradient_flow.png')
    plt.close()
