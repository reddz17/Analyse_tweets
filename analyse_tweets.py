# -*- coding: utf-8 -*-
"""Analyse_tweets.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1eVV8ng7zqvNWU735JuvS3neT6QJ2GNVl

# **TP Textmining** 
#### *Etude portée sur les tweets de politiciens français*

*05-02-2021*

Les objectifs: 
- Travailler sur du texte français.
- Analyser les données 
- Preprocessing des données.
- Découvrir de nouveaux outils : scattertext.
- Prédire qui a posté un tweet.

## **1. Installation des packages**
"""

!pip install scattertext
!pip install spacy
!pip install nltk
!pip install termcolor

!python -m spacy download fr_core_news_md

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time
import datetime


# Modules de traitement du texte
import spacy
import fr_core_news_md
import nltk
import re
from termcolor import colored

# Modules pour le wordcloud
from PIL import Image
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator

# Module pour scattertext
import scattertext as st

# Modules de modélisation
from sklearn.utils.fixes import loguniform
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, classification_report

import os
from google.colab import drive
drive.mount('drive/')

os.chdir('drive/My Drive')

# chemin où se trouve le jeu de données (tweets_politics_2022.csv)
# PATH_DATA = 'drive/My Drive'

"""## **2. Prise en main de la base de données **

Les données ont été extraites via l'API tweepy dans un autre notebook. \
Les tweets de certains candidats à l'élection présidentiels ont été récupérés. 

Regarder les variables à disposition, quelques comptages, s'il y a des données manquantes, quelques graphiques (?), la spécificité des tweets, etc.

#### Import des données
"""

df_tweets = pd.read_csv('tweets_politics_2022.csv', encoding="utf-8")

df_tweets.shape

df_tweets.head()

"""####  Quelques comptages / graphiques

##### Indicateurs simples sur les variables : 
- Y a't'il des données manquantes ? 
- combien de tweets de chaque candidat ? 
- dates minimales / maximales des tweets
- Distribution des favoris et des retweets de chaque candidat
"""

def check_missing_values(df):
  print("check for missing values : ")
  print(df.isnull().sum()/len(df))  
  return

check_missing_values(df_tweets)

# Combien de tweets dans la base de données pour chacun des candidats ? 
df_tweets.groupby("user_id").describe()

# A quelles dates ont été envoyés les premiers / derniers tweets des candidats ? 
df_tweets["created_at"] = pd.to_datetime(df_tweets["created_at"]) 
df_tweets.groupby("user_id").created_at.describe()

df_tweets.groupby(["user_id"])["created_at"].apply(lambda x  : [x.min(), x.max()])

# Quelle est la distribution des favoris et retweets des candidats  ?
df_tweets.groupby("user_id").retweet_count.describe()

df_tweets.groupby("user_id").favorite_count.describe()

"""> On voit que les candidats Emmanuel Macron et Eric Zemmour sont très suivis sur les réseaux

##### Répartition du nombre de retweets / favoris dans le temps
"""

def visualize_count_favorites(df, userID) : 
  
  ''' Cette fonction permet de visualiser le nombre de favoris et de retweets 
  sur toute la période pour un user_id donné '''

  df_temp = df.loc[df["user_id"] == userID]
  ylabels = ["favorite_count", "retweet_count"]

  print("Représentation des nombres de retweets et de favoris de chaque tweet de {} par date".format(userID))
  fig = plt.figure(figsize=(13,3))
  fig.subplots_adjust(hspace=0.01,wspace=0.01)

  n_row = len(ylabels)
  n_col = 1
  for count, ylabel in enumerate(ylabels):
      ax = fig.add_subplot(n_row, n_col, count + 1)
      ax.plot(df_temp["created_at"], df_temp[ylabel])
      ax.set_ylabel(ylabel)
  
  plt.show()

visualize_count_favorites(df_tweets, "JeanLuc_Melenchon")
print("\n")
visualize_count_favorites(df_tweets, "Marine_Lepen")

"""- JLM : 2 tweets ont été plus de 20K fois retweetés (alors qu'en moyenne, un tweet de JLM est retweeté 194 fois) et ont eu donc une grande popularité par rapport à son audience normale. 
- MLP a plutôt une audience stable, avec quelques tweets qui ont été plus retweetés (pic à 4K alors qu'en moyenne un tweet de MLP est retweeté 432 fois).

##### Taille des tweets par politique 

Est-ce que des candidats font des tweets + ou - longs que d'autres ?
"""

# Calcul d'une variable contenant le nombre de mots de chaque tweets
df_tweets["word_count"] = df_tweets["text"].apply(lambda x: len(x.split(" ")))

# Calcul de la distribution de la variable pour chaque politique
df_tweets.groupby("user_id").word_count.describe()

df_tweets

"""##### Lecture de quelques tweets"""

def print_famous_tweets(userID, nb_favorites) :

  ''' Cette fonction permet de sélectionner les tweets qui ont eu le plus de favoris 
  pour un user_id donné, et de lire le tweet avec les indicateurs des autres variables de la 
  base de données  
  '''

  df_sub = df_tweets.loc[(df_tweets.user_id==userID) & (df_tweets.favorite_count > nb_favorites),:]
  for irow in range(df_sub.shape[0]):
      df_row = df_sub.iloc[irow,:]
    
      print(df_row["created_at"])
      print("favorite_count={:6} retweet_count={:6}".format(df_row["favorite_count"],df_row["retweet_count"]))
      print(colored(df_row["text"], 'magenta'))
      print("\n")

# pour comprendre la fonction du dessus
df_tweets.shape[0]

print_famous_tweets("Emmanuel_Macron", 90000)

print_famous_tweets("Eric_Zemmour", 20000)

print_famous_tweets("Marine_Lepen", 10000)

"""> **Question** : Qu'y-a't'il de particulier dans les tweets par rapport à un texte normal ?

On voit que les tweets ont une syntaxe particulère : 
- hashtags 
- liens internet
- emojis

### **Filtres**

- Filtre sur la date pour ne prendre en compte que la campagne électorale (début septembre 2021)
- Filtre sur certains candidats pour que les traitements ne soient pas trop longs
"""

DATE_MIN = "2021-09-01 00:00:00"

df_tweets_temp = df_tweets.loc[df_tweets["created_at"] >= datetime.datetime.strptime(DATE_MIN, "%Y-%m-%d %H:%M:%S")] 

print(f"Taille du dataframe : {len(df_tweets)}")

candidats_select = ["Eric_Zemmour", "Marine_Lepen", "Emmanuel_Macron", "JeanLuc_Melenchon"]
                    
df_tweets_sample = df_tweets_temp.loc[df_tweets_temp.user_id.isin(candidats_select)]

print(f"Taille du dataframe : {len(df_tweets_sample)}")

df_tweets_sample.groupby('user_id').describe()

"""## **3. Preprocessing du texte**

On va prendre en compte les particularités des tweets pour nettoyer le texte. \
On va tester les techniques de preprocessing sur du texte français : 
- stopwords
- lemmatisation
- tokenisation

### Nettoyage du texte
Dans cette partie, on nettoie le texte pour enlever les mots qui vont rajouter du bruit à l'analyse (et ne rien apporter) \
Pour nettoyer le texte : 
- suppression des chiffres
- suppression de certaines expressions grâce à des expressions régulières
- suppression des stopwords
"""

# on charge le modèle français de spacy
nlp = fr_core_news_md.load()
print(len(nlp.Defaults.stop_words))

# on peut rajouter des stopwords à la liste de spacy de cette manière : 
nlp.Defaults.stop_words |= {"avoir", "falloir", "faire", "monsieur", "direct",
                            "interview", "livetweet", "suivez", r"invité\w+", r"(chaîne )?youtube", "mlp"}
                            
# nombre de stopwords 
len(nlp.Defaults.stop_words)

nlp.Defaults.stop_words

"""> **Conseil** :  Toujours regarder la liste entière de stopwords proposés pour enlever certains mots qui seraient utiles dans votre étude ou rajouter des stopwords non présents dans la liste

La cellule ci-dessous donne un exemple d'informations que peut donner Spacy :
"""

doc = nlp("Demain je travaille \\n\\n à la maison. #fatigué @hetik \\n https://test.com")

list_spacy = []
                
for token in doc : 
  list_spacy.append([token.text,
                        token.idx,
                        token.lemma_,
                        token.is_punct,
                        token.is_space,
                        token.is_alpha,
                        token.shape_,
                        token.pos_,
                        token.tag_,
                        token.ent_type_])
  
exemple_spacy = pd.DataFrame(list_spacy, columns=["text", "idx","lemma","is_punct","is_space","is_alpha","shape","pos","tag","ent_type"])
exemple_spacy

"""Expressions régulières pour nettoyer le texte """

regexp_link = re.compile(r"http\S+") # suppression des liens
regexp_number = re.compile(r"\d+[h., ]?\d*") # suppression des chiffres
regexp_hashtags = re.compile(r"[@#]\S+\s+")   # suppression des hashtags et @

"""<details>    
<summary>
    <font size="3" color="darkgreen"><b>Aide</b></font>
</summary>
<p>
Lorsque vous cherchez à créer des expressions régulières, vous pouvez vous aider en allant sur ce site : <a href="https://regex101.com/" >regex101.com</a> 
</p> 
"""

test_hashtags = "#Fuck ça #ne marche @pas !!"
re.sub(regexp_hashtags, "", test_hashtags)

"""Création de la fonction de nettoyage du texte 

Coder plusieurs fonctions :      
- une fonction `clean_text_spacy` qui prend en entrée un tweet et utilise spacy pour :     
    - supprimer les ponctuations ; 
    - supprimer les stopwords ; 
    - supprimer les caractères de type espace (/n, /t, etc.)
Cette fonction garde les tokens entiers
- une fonction `clean_lemmatize` :     
    - supprimer les ponctuations ; 
    - supprimer les stopwords ; 
    - supprimer les caractères de type espace (/n, /t, etc.)
Cette fonction garde non pas les tokens entiers, mais les lemmes. 
- une fonction chapeau `preprocess_tweet` qui : 
  - met les mots en minuscule
  - supprime les mots des expressions régulières
  - au choix applique la fonction `clean_text_spacy` ou `clean_lemmatize`

<details>    
<summary>
    <font size="3" color="darkgreen"><b>Aide</b></font>
</summary>
<p>
Lorsque vous utilisez les fonctions de spacy, vous allez potentiellement les tokeniser directement (et récupérer une liste au lieu d'un texte). Pour éviter cela, transformez le résultat de cette manière :    

```
result = " ".join(result)
```

</p>
"""

def clean_txt_spacy(doc):
  txt = [token.text for token in doc if  (not token.is_stop) and 
                                         (not token.is_punct) and 
                                         (not token.is_space)]
  result = " ".join(txt)
  return result

def clean_lemmatize(doc):
  lemmatized_txt = [token.lemma_ for token in doc if  (not token.is_stop) and 
                                                      (not token.is_punct) and 
                                                      (not token.is_space)]
  lemmatized_txt = " ".join(lemmatized_txt)
  return lemmatized_txt

"""<details>    
<summary>
    <font size="3" color="darkgreen"><b>Aide</b></font>
</summary>
<p>
- Utiliser re.sub() pour supprimer les liens, hashtags, chiffres
</p> 
"""

def preprocess_tweet(text, lemmatizing = True):

  '''Fonction permettant de nettoyer le texte. Elle renvoie un string (pas de tokenisation encore)'''
  text_clean = text.lower().encode('utf-8').decode('utf-8')
  
  # Suppression des liens, hashtags et chiffres avec les regexp précédentes
  text_clean = re.sub(regexp_link, "", text_clean)
  text_clean = re.sub(regexp_hashtags, "", text_clean)
  text_clean = re.sub(regexp_number, "", text_clean)

  doc = nlp(text_clean)  
  if lemmatizing : 
    preprocessed_tweet = clean_lemmatize(doc)
  else : 
    preprocessed_tweet = clean_txt_spacy(doc)

  return preprocessed_tweet

# exemple pour tester sa fonction 
tweet_test = "Ils Pensaient se moquer #non, ils m'ont donné 1 slogan !😄 \n\n- Entretien à découvrir et partager \n\nhttps://t.co/Yn60Areagu"
preprocess_tweet(tweet_test, lemmatizing=True)

# On peut alors nettoyer nos tweets, et créer une nouvelle colonne, text_preprocess
# cela peut prendre un peu de temps à tourner
df_tweets_sample["text_preprocess"] = df_tweets_sample["text"].apply(lambda tweet : preprocess_tweet(tweet, lemmatizing=True))

# On regarde le résultat du nettoyage du texte
pd.set_option("max_colwidth", None)
df_tweets_sample[["text", "text_preprocess"]].head(10)

"""> Le preprocess n'est pas encore parfait, on pourrait enlever les verbes avec du pos-tagging ou bien rajouter l'info de pos-tagging après chaque mot. \
> Supprimer les emojis ou les transformer en texte.

### Tokenisation
On tokenise la colonne de tweets prétraités (preprocess)

**TODO** : utiliser le module nltk pour tokeniser un tweet avec la fonction tokenisation
"""

nltk.download('punkt') # nécessaire pour la tokenisation

def tokenisation(tweet):
  tweet_tokenized = nltk.word_tokenize(tweet)
  return(tweet_tokenized)

df_tweets_sample["tokens"] = df_tweets_sample["text_preprocess"].apply(lambda tweet : tokenisation(tweet))

df_tweets_sample[["text_preprocess", "tokens"]].head()

"""### Analyse du preprocess

On regarde un peu les résultats du preprocessing : 
- combien y a-t-il de mots distincts pour chacun des deux hommes politiques ? 
- Quels sont les mots les plus utilisés par deux candidats de votre choix ? 

Pour cela vous vous aiderez des deux fonctions données ci-dessous
"""

def create_big_tweet_by_userid(userid, col_text) : 

  ''' Fonction pour mettre tous les tweets de chaque politiciens dans un même text (string) '''
  one_big_tweet = " ".join(df_tweets_sample.loc[df_tweets["user_id"] == userid, col_text])
  
  return one_big_tweet

def get_n_most_common_words(list_words, n) :

  ''' Fonction permettant de donner les n mots les plus fréquents d'une liste de mots '''
  freq_words = nltk.FreqDist(list_words)
  print(freq_words.most_common(n))

"""Si on n'utilise pas de preprocessing, quels sont les mots les plus utilisés par les 2 politiciens ?"""

# Créer un gros tweet pour chacun des deux politiques (qui est la jointure de l'ensemble de ses tweets)
big_tweet_candidate1 = create_big_tweet_by_userid("Marine_Lepen", "text")
big_tweet_candidate2 = create_big_tweet_by_userid("Emmanuel_Macron", "text")

# Tokeniser le gros tweet de chacun des politiques
tokens_candidate1 = tokenisation(big_tweet_candidate1)
tokens_candidate2 = tokenisation(big_tweet_candidate2)

# Regarder les 10 mots les plus communs pour chacun des politiques
get_n_most_common_words(tokens_candidate1, 10)
get_n_most_common_words(tokens_candidate2, 10)

"""**Réponse** : les mots les plus utilisés sont des stopwords ou des ponctuations

Sans preprocessing, combien y a-t-il de mots distincts pour chaque politique ?
"""

# la fonction set appliquée sur une liste donne une liste d'éléments uniques
print("Nombre de mots distincts dans les tweets du candidat 1 : {} ".format(len(set(tokens_candidate1))))
print("Nombre de mots distincts dans les tweets du candidat 2 : {} ".format(len(set(tokens_candidate2))))

"""**Réponse** : 

Jean Luc Mélenchon : 11877 \
Eric Zemmour : 8960 \
Marine Lepen : 8108 \
Emmanuel Macron : 4394

Même question avec un preprocessing ?
"""

# Créer un gros tweet pour chacun des deux politiques (qui est la jointure de l'ensemble de ses tweets)
big_tweet_candidate1 = create_big_tweet_by_userid('Marine_Lepen', 'text_preprocess')
big_tweet_candidate2 = create_big_tweet_by_userid('Emmanuel_Macron', 'text_preprocess')

# Tokeniser le gros tweet de chacun des politiques
tokens_candidate1 = tokenisation(big_tweet_candidate1)
tokens_candidate2 = tokenisation(big_tweet_candidate2)

# Regarder les 10 mots les plus communs pour chacun des politiques
get_n_most_common_words(tokens_candidate1, 10)
get_n_most_common_words(tokens_candidate2, 10)

print("Nombre de mots distincts dans les tweets du candidat 1 : {}".format(len(set(tokens_candidate1))))
print("Nombre de mots distincts dans les tweets du candidat 2 : {}".format(len(set(tokens_candidate2))))

"""**Réponse** : 

Jean Luc Mélenchon : 5369 \
Eric Zemmour : 4628   \
Emmanuel Macron :  2765  \
Marine Lepen :  4019

### Nuage de mots

On trace un nuage de mots pour chacun des politiques pour voir ce qui ressort

Faire un nuage de mots pour deux candidats de votre choix avec 30 mots

<details>    
<summary>
    <font size="3" color="darkgreen"><b>Aide</b></font>
</summary>
<p>
<ul>
    <li> transformer l'ensemble des tweets d'un politique en un texte unique </li>
    <li> on peut utiliser la fonction WordCloud </li>
</ul>
</p>
"""

# Faire un texte unique pour les tweets de MLP
def create_wordcloud(text, nb_words):
  wordcloud = WordCloud(max_words=nb_words, background_color="white").generate(text)
  plt.figure()
  plt.imshow(wordcloud, interpolation="bilinear")
  plt.axis("off")
  plt.show()

lemat_candidat1 = " ".join(df_tweets_sample.loc[df_tweets_sample.user_id=="Marine_Lepen", "text_preprocess"])
print("Wordcloud des mots lemmatisés de l'ensemble des tweets de Marine Le Pen")
create_wordcloud(lemat_candidat1, 30)

lemat_candidat2 = " ".join(df_tweets_sample.loc[df_tweets_sample.user_id=="Eric_Zemmour", "text_preprocess"])
print("Wordcloud des mots lemmatisés de l'ensemble des tweets de Eric_Zemmour")
create_wordcloud(lemat_candidat2, 30)

"""C'est bien beau, mais c'est difficile à analyser, et surtout à comparer... \
On va utiliser scattertext pour comparer réellement le vocabulaire des 2 politiques.

## **4. Scattertext**

Grâce à Scattertext, on va pouvoir comparer de manière visuelle la distinction de vocabulaire utilisé par deux candidats de votre choix.

On doit d'abord construire un corpus avec nos données : 
- donner la variable de catégorie 
- donner la variable du texte

On peut rajouter la partie ```.compact(st.AssociationCompactor(4000))``` pour ne prendre en compte que les 4000 mots les plus importants dans le scattertext.

<details>    
<summary>
    <font size="3" color="darkgreen"><b>Aide</b></font>
</summary>
<p>
<ul>
    <li> Filtrer en gardant les tweets des deux candidats de votre choix </li>
</ul>
</p>
"""

df_sample = df_tweets_sample.loc[df_tweets.user_id.isin(["Eric_Zemmour", "JeanLuc_Melenchon"])]

# on crée un objet corpus pour scattertext
corpus = st.CorpusFromPandas(data_frame = df_sample,
                             category_col = "user_id",
                             text_col = "text_preprocess",
                             nlp = nlp).build().compact(st.AssociationCompactor(4000))

"""Une fois le corpus créé, on peut créer le html avec le scattertext. 

On utilise la fonction ```st.produce_scattertext_explorer``` en donnant les paramètres qu'on veut : 
- term_ranker
- term_scorer
- transform 

remplir la fonction en réfléchissant aux paramètres que vous voulez tester :
"""

# On crée le html du scattertext
html = st.produce_scattertext_explorer(  corpus
                                       , category                  = 'Eric_Zemmour'
                                       , category_name             = 'Eric Zemmour'
                                       , not_category_name         = 'Jean Luc Melenchon'
                                       , minimum_term_frequency    = 10
                                       , pmi_threshold_coefficient = 1
                                       , term_ranker               = st.AbsoluteFrequencyRanker
                                       , transform                 = st.Scalers.dense_rank #st.Scalers.log_scale_standardize pour le ScaledFscore
                                       , term_scorer               = st.RankDifference() 
#on peut égalemet tester le term_scorer ScaledFscore : st.ScaledFScorePresets(beta=1, one_to_neg_one=True)
                                       , width_in_pixels           = 1000
                                       )

# On enregistre le html
open("drive/My Drive/tweets_visualisation.html", 'wb').write(html.encode('utf-8'))

Regarder le résultat (il apparaitra dans le drive) en téléchargeant le html (cela peut prendre un petit moment avant de s'afficher correctement).

Analyse du graphique :
On peut voir :
- les mots "stopwords" apparaitre en haut à droite : 
  - des verbes / des mots balises
  - des mots très utilisés dans le langage politique ("France", "politique", "peuple")
- En bas à droite, il y a les mots associés à Jean-Luc Mélenchon : 
  - "retraite", "programme", "populaire", "commun", "humain"
- En haut à gauche, il y a les mots associés à Eric Zemmour : 
  - "Emmanuel Macron", "enfant", "immigration", "étranger", "rural", "civilisation"

## **5. Modélisation**

On souhaite prédire si un tweet provient du compte de Marine Le Pen, de Jean Luc Mélenchon, d'Eric Zemmour ou d'Emmanuel Macron. Pour cela, on a besoin de : 
- Créer un échantillon train / dev
- préparer le text (préprocessing)
- créer des features (plusieurs méthodes : bag of words, counts of words, etc.)
- réaliser l'algorithme
- évaluer la performance du modèle

### Création des échantillons 

Création d'un échantillon train (70% du jeu de données total) et un échantillon test
"""

df_train, df_test, y_train, y_test = train_test_split(df_tweets_sample,
                                                    df_tweets_sample["user_id"], 
                                                    test_size=0.3, 
                                                    random_state=123)

print(f"Nombre de tweets dans l'échantillon train : {len(df_train)}")
print(f"Nombre de tweets dans l'échantillon test : {len(df_test)}")

# on vérifie la répartition entre les user 
print(y_train.value_counts(normalize=True))
print("\n")
print(y_test.value_counts(normalize=True))

"""**Réponse** : 

Nombre de tweets dans l'échantillon train : 4449 \
Nombre de tweets dans l'échantillon test : 1907

On a la même répartition des candidats entre le train et le test. \
Les données ne sont pas équilibrées (Emmanuel Macron a peu de tweets).

### Modèle de régression multinomiale sans gridsearch 

- Transformer le texte de df_train et df_test en vecteurs pour le modèle
- Utiliser la régression logistique multinomiale sans paramètre
- Regarder les paramètres sélectionnés
- Regarder le score sur l'échantillon test

Transformation de df_train pour que ce ne soit plus des tweets, mais des vecteurs grâce à <a href="https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html" >TfidfVectorizer</a>

<details>    
<summary>
    <font size="3" color="darkgreen"><b>Aide</b></font>
</summary>
<p>

La fonction TfidfVectorizer a des paramètres que vous pouvez choisir : 
<ul>

- Combien de n-grams : vous considérez mot par mot ou bien également des groupes de 2 mots
- max_df : si vous voulez enlever un pourcentage de mots les plus fréquents
- min_df : si vous voulez enlever un pourcentage de mots les moins fréquents
</p>
"""

vectorizer = TfidfVectorizer(max_df=0.9, min_df=5, ngram_range=(1, 2))
X_train = vectorizer.fit_transform(df_train['text_preprocess'])

"""Créer le modèle de régression logistique (OVR) et entrainer le modèle sur les données d'apprentissage"""

# initialiser le modèle 
model = LogisticRegression(multi_class="ovr", random_state=54269)

# entrainer le modèle avec les données d'apprentissage
model_default_fit = model.fit(X_train, y_train)

"""NB : le random state permet de figer l'aléatoire, et de trouver toujours les mêmes résultats même en faisant tourner le modèle plusieurs fois. """

# vous pouvez voir les paramètres du modèle 
model_default_fit.get_params(deep=True)

"""Regarder la performance du modèle sur l'échantillon train et test (accuracy)"""

# Sur le train
model_default_fit.score(X_train, y_train)

# Sur le test
X_test = vectorizer.transform(df_test['text_preprocess'])
model_default_fit.score(X_test, y_test)

"""**Résultat** : On voit que le modèle surappend sur l'échantillon train, et qu'il y a de grandes différences de performances entre train et test.

Plus de détails sur ce que donne le modèle :
"""

print("le 1er tweet de l'échantillon test a été prédit : ")
print(model_default_fit.predict(X_test[0]))

print(model_default_fit.classes_) # pour connaître l'ordre des classes / des modèles
model_default_fit.predict_proba(X_test[0])

"""Les résultats des 4 modèles de régression logistique que scikit learn a fait tourner (car on est en One VS rest). 

On voit donc que le 3e modèle qui prédit Jean Luc Mélenchon VS reste, donne la probabilité la plus élevée (0.55 dans mon cas). Scikit learn prédit donc que le 1er tweet vient du compte de Jean Luc Mélenchon

### Mise en place de la RandomSearch

On veut mettre en place une randomSearch pour sélectionner les meilleurs paramètres qu'on a choisi d'évaluer via la méthode de cross-validation : 
- on établit d'abord la grille de paramètres que l'on veut tester
- on effectue la RandomSearch
- on regarde les résultats sur l'échantillon test
"""

# Paramètres à tester données, on peut modifier pour tester d'autres paramètres
dict_params = dict(prep__text_preprocess__max_df=[0.99, 0.95, 0.9],
                   prep__text_preprocess__min_df=[2, 5, 10],
                   clf__C = [1, 20, 50],
                   clf__penalty = ['l2'],
                   clf__multi_class=['ovr', 'multinomial'])

"""Entrainer la Randomsearch avec les paramètres ci-dessus sur les données d'apprentissage avec de la cross validation

NB : une pipeline a été mise en place dans la cellule ci-dessous afin de pouvoir tester également les paramètres du TFIDF. 
"""

# Entrainer le randomizedsearch 

# Vectorisation de la variable text_preprocess
text_transformer_tfidf =  TfidfVectorizer()
preprocess = ColumnTransformer([("text_preprocess", text_transformer_tfidf, "text_preprocess")], 
                               remainder="drop")

# Type de modèle à tester
model = LogisticRegression(random_state=54269, max_iter=1000)

# Pipeline qui combine le preprocess et le modèle
prep_model = Pipeline(steps=[('prep',preprocess),
                             ('clf', model)])

# RANDOMIZED SEARCH
random_search = RandomizedSearchCV( prep_model,
                                   dict_params,
                                   cv=5,  # cross validation de 5 échantillons
                                   n_iter=20,
                                   random_state=5439676,
                                   n_jobs=-1,
                                   verbose=1)

best_rd_model = random_search.fit(df_train, y_train)

# Meilleurs paramètres sélectionnés par la randomSearch
best_rd_model.best_estimator_

"""Quelle accuracy le meilleur modèle a-t'il atteint sur l'échantillon train ? """

# Résultats du meilleur modèle sur l'échantillon train 
best_rd_model.best_score_

"""On évalue la performance en calculant l'accuracy du modèle sélectionné par randomsearch sur l'échantillon test :


"""

best_rd_model.score(df_test, y_test)

"""### Evaluation de la performance du modèle 

On va calculer la matrice de confusion sur l'échantillon test

<details>    
<summary>
    <font size="3" color="darkgreen"><b>Aide</b></font>
</summary>
<p>
<ul>
  <li> Prédire les candidats de df_test dans un premier temps </li>
  <li> Vous pouvez utiliser la fonction <a href="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ConfusionMatrixDisplay.html" >ConfusionMatrixDisplay</a></li>
  
</p>
"""

#matrice de confusion
#confrontation entre Y obs. sur l’éch. test et la prédiction
predictions = best_rd_model.predict(df_test)

cm = confusion_matrix(y_test, 
                      predictions, 
                      labels=best_rd_model.classes_)

disp = ConfusionMatrixDisplay(confusion_matrix=cm,
                              display_labels=best_rd_model.classes_)
disp.plot(cmap=plt.cm.Blues,values_format='g',xticks_rotation='vertical')
plt.show()

"""**Question** : Sur l'ensemble des tweets de JLM, combien (pourcentage) ont bien été prédits JLM ?

**Réponse** : 89% des tweets de JLM ont été prédits JLM par le modèle. 

``` 
728/(728+7+77+26) 

```
"""

#On peut aussi retrouver le résultat via cette fonction
print(classification_report(y_test, best_rd_model.predict(df_test)))

"""On voit que le recall (rappel) sur Emmanuel Macron est très faible (0.45) VS de bons recall pour Jean Luc Mélenchon ou Eric Zemmour.

### Test sur des nouvelles données :

Ces quelques tweets ont été récupérés après que la base de données ait été récupérée. Ce sont donc des nouvelles données que le modèle n'a jamais vu.

**Question** : Qui a publié ces tweets ?
"""

# Visualisation des tweets à prédire
df_mystere = pd.read_excel('test_mystere.xlsx')
df_mystere["text"]

# On prépare les données pour que df_mystere ait la même structure que df_train
df_mystere["text_preprocess"] = df_mystere.text.apply(lambda row : preprocess_tweet(row, lemmatizing=True))
df_mystere["tokens"] = df_mystere.text_preprocess.apply(lambda row : tokenisation(row))

# Réaliser la prédiction avec l'un des deux modèles réalisés
best_rd_model.predict(df_mystere)

"""**Réponse attendue** : 

```
array(['Eric_Zemmour', 'Eric_Zemmour', 'JeanLuc_Melenchon',
       'Emmanuel_Macron', 'JeanLuc_Melenchon'], dtype=object)
```
"""