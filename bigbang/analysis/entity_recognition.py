from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

from spacy.tokens import Span, Doc

from typing import List, Dict
from collections import defaultdict
import re
import contractions


class SpanVisualizer:
    """
    A class to visualize spans. Results are taken from the huggingface models.
    Using spacy for span visualization
    """
    def __init__(self):
        self.ents = []
        self.entity_dict = {}
        self.entity_type = defaultdict(list)

    def get_list_per_type(self):
        if self.entity_dict:
            for ent, type in self.entity_dict.items():
                self.entity_type[type].append(ent)

    def merge_tokens(self, tokens: List):
        """
        A utility function to merge sub-tokenized tokens from huggingface results.
        """
        merged_tokens = []
        # this dictionary is used to store the mapping between the old index with the new merged index
        maps = {}
        merged_token = ''
        for i, token in enumerate(tokens):
            if not merged_token and token.startswith('##'):
                merged_token = merged_tokens.pop()
                merged_token += token[2:]
                maps[i] = len(merged_tokens)
            elif merged_token != '' and token.startswith('##'):
                merged_token += token[2:]
                maps[i] = len(merged_tokens)

            if merged_token == '':
                merged_tokens.append(token)
                maps[i] = len(merged_tokens) - 1
            else:
                if (i == (len(tokens) - 1)) or (i != len(tokens) - 1 and (not tokens[i + 1].startswith('##'))):
                    merged_tokens.append(merged_token)
                    merged_token = ''
        return merged_tokens, maps

    def get_type(self, label: Dict):
        return label['entity'].split('-')[-1]

    def get_map_index(self, label: Dict, maps: Dict):
        # get the mapped index from the merged tokens
        return maps[label['index'] - 1]

    def is_same(self, label: Dict, p_label: Dict, maps: Dict):
        return (self.get_type(label) == self.get_type(p_label)) and (
                    self.get_map_index(label, maps) - self.get_map_index(p_label, maps) <= 1)

    def merge_labels(self, labels: List, maps: Dict):
        # we merge the tokens that are consecutive with the same type as one entity mention
        merged_labels = []
        stack = []
        # if the stack is empty we push the new label to the stack, else:
        # check if the label is within the same entity mention, if it is, we push into the stack, else:
        # we merge all the labels in the stack and pop it to the merged labels
        for i, label in enumerate(labels):
            if stack:
                prev_label = stack[-1]
                if self.is_same(label, prev_label, maps):
                    stack.append(label)
                else:
                    merged_labels.append(stack)
                    stack = [label]
            else:
                stack.append(label)
        if stack:
            merged_labels.append(stack)
        return merged_labels

    def get_doc_for_visualization(self, merged_labels: List, maps: Dict, doc: Doc):
        ents = []
        starts = []

        for m_labels in merged_labels:
            start = self.get_map_index(m_labels[0], maps)
            end = self.get_map_index(m_labels[-1], maps) + 1
            entity_type = self.get_type(m_labels[0])
            if start not in starts:
                ent = Span(doc, start, end, entity_type)
                self.entity_dict[str(ent)] = entity_type
                ents.append(ent)
                starts.append(start)
        doc.set_ents(ents)
        self.ents.extend(ents)
        return doc


class EntityRecognizer:
    def __init__(self, model_name: str="dslim/bert-base-NER"):
        self.entities = []
        self.model_name = model_name

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
        self.nlp = pipeline("ner", model=self.model, tokenizer=self.tokenizer)

    def remove_ori_message(self, body: str):
        """
        A function to remove the original message in a hard-coded way
        """
        body = body.split('---- Original Message ----')[0]
        return body


    def pre_processing(self, body: str, lowercase: bool=False):
        """
        A function to pre-process the email bodies. Including:
        - expand contractions
        - remove punctuations
        - remove links
        - remove all digits
        - remove extra spaces and newlines
        """
        # expand contractions
        body = contractions.fix(body)
        # remove punctuations
        body = re.sub(r'[^\w\s]', '', body)
        # remove links
        body = re.sub(r"http\S+", "", body)
        # remove all digits
        body = re.sub(r'\d+', '', body)
        # remove extra spaces and newlines
        body = body.strip()
        body = body.replace("\n", " ")
        body = body.replace("\t", " ")
        if lowercase:
            body = body.lower()
        return body

    def recognize(self, data: str):
        """
        A wrapper for huggingface NER models.
        """
        return self.nlp(data)

    def get_entities(self, tags: List):
        """
        A function process results from huggingface models and
        get only the mentions and corresponding entity types
        """
        entities = []
        for tag in tags:
            name_type = {}
            name_type['entity'] = tag['entity']
            name_type['word'] = tag['word']
            entities.append(name_type)
        self.entities = entities
        return entities
