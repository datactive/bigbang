# import necessary packages
from bigbang.archive import Archive
from bigbang.archive import load as load_archive

from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

import spacy
from spacy.tokens import Span, Doc
from spacy.util import filter_spans

import pandas as pd

from typing import List, Dict
from collections import defaultdict
import re
import contractions
from email_reply_parser import EmailReplyParser


class SpanVisualizer:
    """
    A class to visualize spans. Results are taken from the huggingface models.
    Using spacy for span visualization
    """

    def __init__(self):
        self.ents = []
        self.entity_dict = {}
        self.entity_type = defaultdict(list)
        self.merged_tokens = None
        self.merged_labels = None
        self.maps = None

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
        merged_token = ""
        for i, token in enumerate(tokens):
            if not merged_token and token.startswith("##"):
                merged_token = merged_tokens.pop()
                merged_token += token[2:]
                maps[i] = len(merged_tokens)
            elif merged_token != "" and token.startswith("##"):
                merged_token += token[2:]
                maps[i] = len(merged_tokens)

            if merged_token == "":
                merged_tokens.append(token)
                maps[i] = len(merged_tokens) - 1
            else:
                if (i == (len(tokens) - 1)) or (
                    i != len(tokens) - 1 and (not tokens[i + 1].startswith("##"))
                ):
                    merged_tokens.append(merged_token)
                    merged_token = ""
            self.merged_tokens = merged_tokens
            self.maps = maps
        return merged_tokens

    def get_type(self, label: Dict):
        return label["entity"].split("-")[-1]

    def get_map_index(self, label: Dict, maps: Dict):
        # get the mapped index from the merged tokens
        return maps[label["index"] - 1]

    def is_same(self, label: Dict, p_label: Dict, maps: Dict):
        return (self.get_type(label) == self.get_type(p_label)) and (
            self.get_map_index(label, maps) - self.get_map_index(p_label, maps) <= 1
        )

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
        self.merged_labels = merged_labels
        return merged_labels

    def find_all_cap_ents(self, body: str, merged_tokens: list, doc: Doc):
        # currently only supports single token all_cap words
        # match all_cap words and find their positions
        pattern = "[A-Z]+[A-Z]+[A-Z]*[\s]+"
        all_caps = re.findall(pattern, body)
        all_caps = [s.strip() for s in all_caps]
        # find the words in the tokens
        indexes = []
        for word in all_caps:
            for i, t in enumerate(merged_tokens):
                if t == word:
                    if i not in indexes:
                        indexes.append(i)
                        break
        # curating identified indexes list
        rec_positions = []
        for ent in self.ents:
            for pos in range(ent.start, ent.end + 1):
                rec_positions.append(pos)
        # if not, adding to the entity list
        entity_type = "ALLCAPS"
        all_cap_ents = []
        for start in indexes:
            if start not in rec_positions:
                end = start + 1
                ent = Span(doc, start, end, entity_type)
                # TODO: includnig differnet entities with the same names
                self.entity_dict[str(ent)] = entity_type
                all_cap_ents.append(ent)
        self.ents.extend(all_cap_ents)
        # for ent in self.ents:
        #     print(ent.start)
        # print(self.ents)
        doc.set_ents(self.ents)
        return doc

    def get_doc_for_visualization(
        self,
        tokens: List,
        labels: list,
        body: str,
        doc: Doc,
        find_all_caps: bool = True,
    ):
        if not self.merged_tokens or self.maps:
            _ = self.merge_tokens(tokens)
        if not self.merged_labels:
            _ = self.merge_labels(labels, self.maps)

        ents = []
        starts = []

        for m_labels in self.merged_labels:
            start = self.get_map_index(m_labels[0], self.maps)
            end = self.get_map_index(m_labels[-1], self.maps) + 1
            entity_type = self.get_type(m_labels[0])
            if start not in starts:
                ent = Span(doc, start, end, entity_type)
                self.entity_dict[str(ent)] = entity_type
                ents.append(ent)
                starts.append(start)
        self.ents.extend(ents)
        self.ents = filter_spans(self.ents)
        doc.set_ents(self.ents)
        if find_all_caps:
            doc = self.find_all_cap_ents(body, self.merged_tokens, doc)
        return doc


class EntityRecognizer:
    def __init__(self, model_name: str = "dslim/bert-base-NER"):
        self.entities = []
        self.model_name = model_name

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
        self.nlp = pipeline("ner", model=self.model, tokenizer=self.tokenizer)

    def remove_ori_message(self, body: str):
        """
        A function to remove the original message using package parsing
        """
        body = EmailReplyParser.parse_reply(body)
        return body

    def pre_processing(self, body: str, lowercase: bool = False):
        """
        A function to pre-process the email bodies. Including:
        - expand contractions
        - remove punctuations
        - remove links
        - remove all digits
        - remove extra spaces and newlines
        """
        # parse reply
        body = self.remove_ori_message(body)
        # expand contractions
        body = contractions.fix(body)
        # # remove punctuations
        # body = re.sub(r'[^\w\s]', '', body)
        # remove links
        body = re.sub(r"http\S+", "", body)
        # remove all digits
        body = re.sub(r"\d+", "", body)
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
            name_type["entity"] = tag["entity"]
            name_type["word"] = tag["word"]
            entities.append(name_type)
        self.entities = entities
        return entities


pronouns = [
    "i",
    "you",
    "me",
    "my",
    "mine",
    "myself",
    "your",
    "yours",
    "yourself",
    "we",
    "us",
    "our",
    "ours",
    "ourselves",
    "yourselves",
    "he",
    "him",
    "himself",
    "his",
    "she",
    "her",
    "hers",
    "herself",
    "it",
    "its",
    "itself",
    "they",
    "them",
    "their",
    "theirs",
    "themself",
    "themselves",
    "this",
    "that",
    "something",
    "these",
    "those",
    "someone",
    "somebody",
    "who",
    "whom",
    "whose",
    "which",
    "what",
]


def process_list_entities(mailing_list="scipy-dev"):
    mailing_list = "../../archives/scipy-dev/"

    archive = Archive(mailing_list, mbox=True)
    # archive data in pandas dataframe format
    archive_data = archive.data
    # taking a list of indexes as examples
    num_data = len(archive_data)
    num_data = 10
    print("Process {} emails in total".format(num_data))
    indexes = list(range(0, num_data))
    lowercase = False
    find_all_caps = True

    model_name = "EffyLi/bert-base-NER-finetuned-ner-cerec"
    # model_name = "dslim/bert-base-NER"
    recognizer = EntityRecognizer(model_name)

    nlp = spacy.load("en_core_web_sm")
    vocab = nlp.tokenizer.vocab
    save_file_name = mailing_list.split("/")[-2] + "-entities.csv"
    columns_names = ["email_id", "entity", "type"]
    df = pd.DataFrame(columns=columns_names)

    email_entity_types = defaultdict(list)

    # print('Process emails with id: ', indexes)
    for index in indexes:
        if index % 200 == 0:
            print(
                "{} emails processed, {} emails left.".format(index, (num_data - index))
            )
        body = list(archive_data["Body"].iloc[[index]])[0]
        body = recognizer.pre_processing(body, lowercase=lowercase)

        visualizer = SpanVisualizer()
        # get labels from recognizer first
        tokens = recognizer.tokenizer.tokenize(body)
        labels = recognizer.recognize(body)
        # merge tokens and spans in visualizer
        merged_tokens = visualizer.merge_tokens(tokens)
        doc = Doc(vocab=vocab, words=merged_tokens)
        doc = visualizer.get_doc_for_visualization(
            tokens, labels, body, doc, find_all_caps
        )
        visualizer.get_list_per_type()
        entity_type = visualizer.entity_type
        for k, v in entity_type.items():
            email_entity_types[k].extend(v)
            for v_i in v:
                # remove pronouns
                if v_i.lower() not in pronouns:
                    new_row = {"email_id": index, "entity": v_i, "type": k}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(save_file_name)
    print("Extracted entities saved!")
