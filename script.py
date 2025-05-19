import urllib.parse
import requests
from collections import defaultdict
import json
from typing import List
# import nltk
# from nltk.corpus import stopwords 
import yaml
import re

with open("config.yml", 'r') as config_file:
    config = yaml.safe_load(config_file)

min_len_ngram = config['ngram_settings']['min_len_ngram']
max_len_ngram = config['ngram_settings']['max_len_ngram']
probable_product_threshold = config['ngram_settings']['probable_product_threshold']
product_eligibility_count = config['ngram_settings']['product_eligibility_count']

server = config['solr_settings']['server']
port_number = config['solr_settings']['port_number']
mcat_search_solr_path = config['solr_settings']['mcat_search_solr_path']


# nltk.download('stopwords')
# STOP_WORDS = set(stopwords.words('english'))


def generate_ngrams(text: str, min_words: int, max_words: int) -> List[str]:
    words = text.split()
    # words = [word for word in words if word not in STOP_WORDS]

    ngrams = []

    if min_words > len(words):
        return ngrams

    max_words = min(max_words, len(words))

    for n in range(min_words, max_words + 1):
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i + n])
            ngrams.append(ngram)

    return ngrams

def get_Solr_results(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return {}

def balance_brackets(s):
    stack = []
    result = list(s)
    matching = {')': '(', '}': '{', ']': '['}
    opening = set(matching.values())
    closing = set(matching.keys())
    remove_indices = set()

    for i, char in enumerate(s):
        if char in opening:
            stack.append((char, i))
        elif char in closing:
            if stack and stack[-1][0] == matching[char]:
                stack.pop()
            else:
                remove_indices.add(i)

    # Remaining unmatched opening brackets
    remove_indices.update(index for (_, index) in stack)

    # Build result string by skipping invalid bracket indices
    return ''.join(char for i, char in enumerate(result) if i not in remove_indices)

def split_by_brackets(text):
    parts = []
    pattern = r'\(|\)|\{|\}|\[|\]'
    stack = []
    current = ''
    i = 0
    while i < len(text):
        char = text[i]
        if char in '({[':
            if current.strip():
                parts.append(current.strip())
            current = ''
            i += 1
            # collect text inside brackets
            inner = ''
            bracket_count = 1
            while i < len(text) and bracket_count > 0:
                if text[i] in '({[':
                    bracket_count += 1
                elif text[i] in ')}]':
                    bracket_count -= 1
                    if bracket_count == 0:
                        i += 1
                        break
                if bracket_count > 0:
                    inner += text[i]
                    i += 1
            if inner.strip():
                parts.append(inner.strip())
            current = ''
        else:
            current += char
            i += 1
    if current.strip():
        parts.append(current.strip())
    return parts

def split_by_commas(parts_list):
    final_parts = []
    for part in parts_list:
        buffer = ''
        for char in part:
            if char == ',':
                if buffer.strip():
                    final_parts.append(buffer.strip())
                buffer = ''
            else:
                buffer += char
        if buffer.strip():
            final_parts.append(buffer.strip())
    return final_parts

def split_by_prepositions(parts_list):
    prepositions = {"with", "by", "in", "at", "on", "through", "to", "of", "from", "for", "as"}
    final_parts = []

    for part in parts_list:
        words = part.strip().split()
        buffer = []
        for word in words:
            if word.lower() in prepositions:
                if buffer:
                    final_parts.append(" ".join(buffer).strip())
                    buffer = []
            else:
                buffer.append(word)
        if buffer:
            final_parts.append(" ".join(buffer).strip())

    return final_parts

def process_query(query,all_ngrams_with_cnt,probable_Product):

    all_ngrams = generate_ngrams(query,min_len_ngram,max_len_ngram)
    all_ngrams.reverse()

    for gram in all_ngrams:
        titlex = urllib.parse.quote(f"imsws {gram} imswe")
        each_gram_url = ( f"http://{server}:{port_number}/{mcat_search_solr_path}?q=%22{titlex}%22&defType=edismax&df=title_exact&qt=title.search&fl=*&echoParams=all&rows=1&source=gladmin.appsmith.coresearcher&queryname=ngrams")
        result = get_Solr_results(each_gram_url)

        if 'response' in result and 'numFound' in result['response']:
            num_found = result['response']['numFound']
            all_ngrams_with_cnt.append({ gram : num_found })
            if num_found >= product_eligibility_count and len(probable_Product) < probable_product_threshold: 
                probable_Product.append(gram)

        else: 
            all_ngrams_with_cnt.append({ gram : 0 })
    

def process_search_str(search_str):
    all_ngrams_with_cnt = []    #storing all ngrams possible with their numFound value 
    probable_Product = []     #storing probable products
    balanced_brackets_search_str = balance_brackets(search_str)
    if len(balanced_brackets_search_str.split())==0:
        return  all_ngrams_with_cnt , probable_Product
    
    bracket_splitted_queries = split_by_brackets(balanced_brackets_search_str)
    if len(bracket_splitted_queries)==0:
        return  all_ngrams_with_cnt , probable_Product
    
    comma_splitted_queries = split_by_commas(bracket_splitted_queries)
    if len(comma_splitted_queries)==0:
        return  all_ngrams_with_cnt , probable_Product
    
    all_possible_query = split_by_prepositions(comma_splitted_queries)
    if len(comma_splitted_queries)==0:
        return  all_ngrams_with_cnt , probable_Product
    
    for query in all_possible_query:
        process_query(query,all_ngrams_with_cnt,probable_Product)

    return all_ngrams_with_cnt , probable_Product 

