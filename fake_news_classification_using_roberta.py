# -*- coding: utf-8 -*-
"""Fake News Classification using ROBERTA.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1iejng-AlkQXDhhOcrJULhC8mvihIUYOb

# Deep Learning for NLP

**Fake news classifier**: Train a text classification model to detect fake news articles!

* Download the dataset here: https://www.kaggle.com/clmentbisaillon/fake-and-real-news-dataset
"""

### WRITE YOUR CODE TO TRAIN THE MODEL HERE

from google.colab import drive
drive.mount('/content/drive')

!pip install transformers

import seaborn as sns
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import nltk
import pandas as pd
import numpy as np

nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger') 
import gensim
from nltk import word_tokenize
from tensorflow.keras.preprocessing.text import one_hot, Tokenizer
from nltk.corpus import stopwords
from tensorflow.keras.preprocessing.sequence import pad_sequences

import sklearn
import itertools
from sklearn.utils import shuffle
from sklearn.metrics import roc_curve, roc_auc_score, auc
from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

# from tqdm.notebook import tqdm
from tqdm.auto import tqdm
import torch
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
from torch.nn.utils.rnn import pad_sequence
from torch.optim import AdamW

from transformers import BertTokenizer
from transformers import BertForSequenceClassification
from transformers import RobertaForSequenceClassification, RobertaTokenizer
from transformers import AutoModelForSequenceClassification
from transformers import get_scheduler


from IPython.display import display, clear_output

print('Done')

# Commented out IPython magic to ensure Python compatibility.
# %load_ext autoreload
# %autoreload 2

true_path = '/content/drive/MyDrive/archive/True.csv'
fake_path = '/content/drive/MyDrive/archive/Fake.csv'

true_df = pd.read_csv(true_path)
fake_df = pd.read_csv(fake_path)

display(true_df)
display(fake_df)

"""Data Visualization"""

sns.countplot(y="subject", palette="coolwarm", data=true_df).set_title('True News Subject Distribution')
plt.show()

sns.countplot(y="subject", palette="coolwarm", data=fake_df).set_title('Fake News Subject Distribution')
plt.show()

"""Word Cloud"""

real_titles = true_df.title
real_titles_ls = [text for text in real_titles]
# print(alls)
real_all_words = ' '.join(real_titles)
wordcloud_real = WordCloud(background_color='white',
    width= 800, height= 500,
    max_font_size = 180,
    collocations = False).generate(real_all_words)

plt.figure(figsize=(10,7))
plt.imshow(wordcloud_real, interpolation='bilinear')
plt.axis("off")
plt.show()

fake_titles = fake_df.title
fake_titles_ls = [text for text in fake_titles]
# print(alls)
fake_all_words = ' '.join(fake_titles)
wordcloud_fake = WordCloud(background_color='white',
    width= 800, height= 500,
    max_font_size = 180,
    collocations = False).generate(fake_all_words)

plt.figure(figsize=(10,7))
plt.imshow(wordcloud_fake, interpolation='bilinear')
plt.axis("off")
plt.show()

"""Data Preprocessing"""

# Add Labels to both df
true_df['true'] = 1
fake_df['true'] = 0

# Concat
df = pd.concat([true_df, fake_df])
display(df)

titles = [text for text in df.title]

max_len = 0
titles_len = []
for title in titles:
    titles_len.append(len(title.split()))
    max_len = max(len(title.split()), max_len)

print('Number of titles:', len(titles))
print('Max length of the titles:', max_len)
print('Mean length of the titles:', np.mean(titles_len))

# plt.figure(figsize=(20,5))
# g = sns.countplot(x=titles_len)
# g.set_xticklabels(g.get_xticklabels(), rotation=50)
# plt.show()

texts = [text for text in df.text]

max_len = 0
texts_len = []
for text in texts:
    texts_len.append(len(text.split()))
    max_len = max(len(text.split()), max_len)

# g = sns.countplot(x=texts_len)
print('Mean length of the texts:', np.mean(texts_len))

"""Data Shuffling"""

df = df.iloc[:,[0, -1]]

df = shuffle(df).reset_index(drop=True)

display(df)

"""Splitting into train, test and validation set"""

train_val_df = df.sample(frac = 0.8)
test_df = df.drop(train_val_df.index)

train_df = train_val_df.sample(frac = 0.8)
val_df = train_val_df.drop(train_df.index)

# Reset Index
train_df = train_df.reset_index(drop=True)
val_df = val_df.reset_index(drop=True)
test_df = test_df.reset_index(drop=True)

print('trainset size:', train_df.shape)
print('valset size:', val_df.shape)
print('testset size:', test_df.shape)

df = pd.concat([train_df, val_df, test_df])
display(df)

"""Performing Data Cleaning"""

# Obtaining Additional Stopwords From nltk
stop_words = stopwords.words('english')
# Removing Stopwords
def preprocess(text):
    result = []
    for token in gensim.utils.simple_preprocess(text):
        if token not in gensim.parsing.preprocessing.STOPWORDS and token not in stop_words:
            result.append(token)
            
    return result

df['clean'] = df['title'].apply(preprocess)

list_of_words = []
for i in df.clean:
    for j in i:
        list_of_words.append(j)



total_words = len(list(set(list_of_words)))
total_words

"""ROBERT"""

train_df.to_csv('train.tsv', sep='\t', index=False)
val_df.to_csv('val.tsv', sep='\t', index=False)
test_df.to_csv('test.tsv', sep='\t', index=False)

# roberta_model = RobertaForSequenceClassification.from_pretrained("roberta-base", #RoBERTa base model
#                                                                     num_labels = 2,  #number of output labels - 0,1 (binary classification)
#                                                                     output_attentions = False,  #model doesnt return attention weights
#                                                                     output_hidden_states = False #model doesnt return hidden states
#                                                                 )
# #RoBERTa tokenizer
# roberta_tokenizer = RobertaTokenizer.from_pretrained("roberta-base", do_lower_case=True)
PRETRAINED_MODEL_NAME = 'roberta-base'
tokenizer = RobertaTokenizer.from_pretrained(PRETRAINED_MODEL_NAME, do_lower_case=True)

class FakeNewsDataset(Dataset):
    def __init__(self, mode, tokenizer):
        assert mode in ['train', 'val', 'test']
        self.mode = mode
        # shuffle(df).reset_index(drop=True)
        self.df = shuffle(pd.read_csv('/content/' + mode + '.tsv', sep='\t').fillna("")).reset_index(drop=True)
        self.len = len(self.df)
        self.tokenizer = tokenizer  # ROBERT tokenizer
    
    def __getitem__(self, idx):
        if self.mode == 'test':
            statement, label = self.df.iloc[idx, :].values
            label_tensor = torch.tensor(label)
        else:
            statement, label = self.df.iloc[idx, :].values
            label_tensor = torch.tensor(label)
            
        word_pieces = ['[CLS]']
        statement = self.tokenizer.tokenize(statement)
        word_pieces += statement + ['[SEP]']
        len_st = len(word_pieces)
        
        ids = self.tokenizer.convert_tokens_to_ids(word_pieces)
        tokens_tensor = torch.tensor(ids)
        
        segments_tensor = torch.tensor([0] * len_st, dtype=torch.long)
        
        return (tokens_tensor, segments_tensor, label_tensor)

    def __len__(self):
        return self.len
  
    
trainset = FakeNewsDataset('train', tokenizer=tokenizer)
valset = FakeNewsDataset('val', tokenizer=tokenizer)
testset = FakeNewsDataset('test', tokenizer=tokenizer)

print('trainset size:' , len(trainset.df))
print('valset size:', len(valset.df))
print('testset size:', len(testset.df))

"""Observing tensors"""

sample_idx = 0

statement, label = trainset.df.iloc[sample_idx].values

tokens_tensor, segments_tensor, label_tensor = trainset[sample_idx]

tokens = tokenizer.convert_ids_to_tokens(tokens_tensor.tolist())
combined_text = " ".join(tokens)

print(f"""original_statement: {statement} tokens: {tokens} label: {label}
-------------------- tokens_tensor: {tokens_tensor} segments_tensor: {segments_tensor} label_tensor: {label_tensor}""")

def create_mini_batch(samples):
    tokens_tensors = [s[0] for s in samples]
    segments_tensors = [s[1] for s in samples]
    
    if samples[0][2] is not None:
        label_ids = torch.stack([s[2] for s in samples])
    else:
        label_ids = None
    
    # Zero Padding
    tokens_tensors = pad_sequence(tokens_tensors, batch_first=True)
    segments_tensors = pad_sequence(segments_tensors, batch_first=True)
    
    masks_tensors = torch.zeros(tokens_tensors.shape, dtype=torch.long)
    masks_tensors = masks_tensors.masked_fill(tokens_tensors != 0, 1)
    
    return tokens_tensors, segments_tensors, masks_tensors, label_ids


BATCH_SIZE = 32
trainloader = DataLoader(trainset, shuffle=True, batch_size=BATCH_SIZE, collate_fn=create_mini_batch)
valloader = DataLoader(valset, batch_size=BATCH_SIZE, collate_fn=create_mini_batch)
testloader = DataLoader(testset, batch_size=BATCH_SIZE,collate_fn=create_mini_batch)

data = next(iter(trainloader))

tokens_tensors, segments_tensors, masks_tensors, label_ids = data

print(f"""
tokens_tensors.shape   = {tokens_tensors.shape} 
{tokens_tensors}
------------------------
segments_tensors.shape = {segments_tensors.shape}
{segments_tensors}
------------------------
masks_tensors.shape    = {masks_tensors.shape}
{masks_tensors}
------------------------
label_ids.shape        = {label_ids.shape}
{label_ids}
""")

"""Model construction"""

# roberta_model = RobertaForSequenceClassification.from_pretrained("roberta-base", #RoBERTa base model
#                                                                     num_labels = 2,  #number of output labels - 0,1 (binary classification)
#                                                                     output_attentions = False,  #model doesnt return attention weights
#                                                                     output_hidden_states = False #model doesnt return hidden states
#                                                                 )
# #RoBERTa tokenizer
# roberta_tokenizer = RobertaTokenizer.from_pretrained("roberta-base", do_lower_case=True)

PRETRAINED_MODEL_NAME = "roberta-base"
NUM_LABELS = 2

# model = BertForSequenceClassification.from_pretrained(
#     PRETRAINED_MODEL_NAME, num_labels=NUM_LABELS)

model = RobertaForSequenceClassification.from_pretrained(
    PRETRAINED_MODEL_NAME, num_labels=NUM_LABELS)


clear_output()

print("""
name             module
-----------------------""")
for name, module in model.named_children():
    if name == "bert":
        for n, _ in module.named_children():
            print(f"{name}:{n}")
    else:
        print("{:16} {}".format(name, module))

model.config

"""Fine tuning of ROBERT"""

def validation_check(model, valloader):
    true = []
    predictions = []
    model.eval()
    val_accuracy = []
    val_loss = []
    
    loop2 = tqdm(valloader)
    for batch_idx, data in enumerate(loop2):
        tokens_tensors, segments_tensors, masks_tensors, labels = [t.to(device) for t in data]
    # for data in valloader:
    #     if next(model.parameters()).is_cuda:
    #         data = [t.to(device) for t in data if t is not None]
            
        # tokens_tensors, segments_tensors, masks_tensors = data[:3]
        test_outputs = model(input_ids=tokens_tensors, 
                    token_type_ids=segments_tensors, 
                    attention_mask=masks_tensors,
                    labels = labels)

        logits = test_outputs[1]
        _, pred = torch.max(logits.data, 1)
        
        # true.extend(labels.cpu().tolist())
        # predictions.extend(pred.cpu().tolist())

        val_accuracy.append(accuracy_score(pred.cpu().tolist() , labels.cpu().tolist()))
        # val_loss.append(loss.item())
        # val_accuracy.append(accuracy_score(predictions,true))

    # val_loss = np.mean(val_loss)
    val_accuracy = np.mean(val_accuracy)

    return val_accuracy

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print("device:", device)
model = model.to(device)

# model.train()
# optimizer = torch.optim.Adam(model.parameters(), lr=1e-5)
optimizer = AdamW(model.parameters(), lr=1e-5)
num_epochs = 5
num_training_steps = num_epochs * len(trainloader)
lr_scheduler = get_scheduler(name="linear", optimizer=optimizer, num_warmup_steps=0, num_training_steps=num_training_steps)

# progress_bar = tqdm(range(num_training_steps))

model.train()

for epoch in range(num_epochs):
    train_loss = 0.0
    train_acc = 0.0

    loop = tqdm(trainloader)
    for batch_idx, data in enumerate(loop):
        tokens_tensors, segments_tensors, masks_tensors, labels = [t.to(device) for t in data]

    
        # optimizer.zero_grad()
        
        outputs = model(input_ids=tokens_tensors, 
                        token_type_ids=segments_tensors, 
                        attention_mask=masks_tensors, 
                        labels=labels)

  

        loss = outputs[0]
        loss.backward()
        optimizer.step()
        lr_scheduler.step()
        optimizer.zero_grad()
        

        logits = outputs[1]
        _, pred = torch.max(logits.data, 1)
        train_acc = accuracy_score(pred.cpu().tolist() , labels.cpu().tolist())

        train_loss += loss.item()

        # progress_bar.update(1)

        loop.set_description(f"Epoch [{epoch+1}/{num_epochs}]")
        loop.set_postfix(acc = train_acc, loss = train_loss)
    
    val_accuracy = validation_check(model, valloader)
    print(f" validation accuracy {val_accuracy} \n")

"""Save Model"""

torch.save(model, 'best_model.pth')
print('Model saved!')

"""Load Model"""

model = torch.load('./content/best_model.pth')
model = model.to(device)

"""Test"""

true=[]
predictions=[]
with torch.no_grad():
    model.eval()
    for data in testloader:
        if next(model.parameters()).is_cuda:
            data = [t.to(device) for t in data if t is not None]
            
        tokens_tensors, segments_tensors, masks_tensors = data[:3]
        test_outputs = model(input_ids=tokens_tensors, 
                    token_type_ids=segments_tensors, 
                    attention_mask=masks_tensors)

        logits = test_outputs[0]
        _, pred = torch.max(logits.data, 1)

        labels = data[3]
        true.extend(labels.cpu().tolist())
        predictions.extend(pred.cpu().tolist())


cm = confusion_matrix(true, predictions, labels=[1, 0], normalize='pred')
print(cm)

disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['Real', 'Fake'])
disp.plot()

print('Acc: ', accuracy_score(predictions,true))

df = pd.DataFrame({"pred_label": predictions})

df_pred = pd.concat([testset.df.loc[:, ['title']], 
                          testset.df.loc[:, ['true']], 
                          df.loc[:, 'pred_label']], axis=1)
# df_pred.to_csv('bert_1_prec_training_samples.csv', index=False)
df_pred

print(sklearn.metrics.classification_report(df_pred.true, df_pred.pred_label))

"""AUC-ROC CURVE"""

bert_fpr, bert_tpr, threshold = roc_curve(df_pred.true, df_pred.pred_label)
auc_bert = auc(bert_fpr, bert_tpr)

plt.figure(figsize=(5, 5), dpi=100)
plt.plot(bert_fpr, bert_tpr, linestyle='-', label='BERT (auc = %0.4f)' % auc_bert)

plt.xlabel('False Positive Rate -->')
plt.ylabel('True Positive Rate -->')

plt.legend()

plt.show()

wrong_df = df_pred[df_pred.true != df_pred.pred_label]
sns.countplot(y="true", palette="coolwarm", data=wrong_df).set_title('Wrong Classification Result Real/Fake Distribution')
plt.show()

wrong_news = df_pred[df_pred.true != df_pred.pred_label]
print(wrong_news.to_string())