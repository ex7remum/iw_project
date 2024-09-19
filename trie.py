from graphviz import Digraph
import logging
from functools import lru_cache
import pandas as pd
import time

def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Функция {func.__name__} выполнена за {end_time - start_time:.4f} секунд")
        return result
    return wrapper

class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False

logging.basicConfig(level=logging.DEBUG)


def load_medicines_to_trie(trie):
    drugs_data = pd.read_csv('medicines.csv', sep=';')
    if trie.lang == 'en':
        for drug in drugs_data['Drug_name_en']:  # Load only English names for the autocomplete
            trie.insert(drug.lower())
    else:
        for drug in drugs_data['Drug_name_rus']:  # Load only Russian names for the autocomplete
            trie.insert(drug.lower())
    #trie_visualizer = TrieVisualizer(medicine_trie)
    #trie_visualizer.draw().render("trie_structure", format="png", view=True)

class Trie:
    @timeit
    @lru_cache(maxsize=3)
    def __init__(self, lang):
        print('Trie created')
        self.root = TrieNode()
        self.lang = lang
        load_medicines_to_trie(self)

    def insert(self, word):
        #logging.debug(f"Inserting word: {word}")
        word = word.lower()  # Ensure all words are inserted as lowercase
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        #logging.debug(f"Word '{word}' inserted successfully.")

    def search_prefix(self, prefix):
        logging.debug(f"Searching for prefix: {prefix}")
        prefix = prefix.lower()  # Ensure prefix search is case-insensitive
        node = self.root
        for char in prefix:
            if char not in node.children:
                logging.debug(f"Prefix '{prefix}' not found.")
                return None
            node = node.children[char]
        logging.debug(f"Prefix '{prefix}' found.")
        return node

    def autocomplete(self, prefix):
        prefix = prefix.strip()
        logging.debug(f"Autocomplete called with prefix: {prefix}")
        node = self.search_prefix(prefix)
        if not node:
            logging.debug(f"No suggestions for prefix: {prefix}")
            return []
        suggestions = self._find_words(node, prefix)
        logging.debug(f"Suggestions for '{prefix}': {suggestions}")
        return suggestions

    def _find_words(self, node, prefix):
        words = []
        if node.is_end_of_word:
            words.append(prefix)
        for char, next_node in node.children.items():
            words.extend(self._find_words(next_node, prefix + char))
        return words

class TrieVisualizer(Trie):
    def __init__(self):
        super().__init__()

    def draw(self):
        dot = Digraph()
        dot.attr('node', shape='circle')
        self._add_edges(self.root, dot, "")
        return dot

    def _add_edges(self, node, dot, prefix):
        for char, child_node in node.children.items():
            new_prefix = prefix + char
            dot.node(new_prefix, char)  # Add node for the character
            if prefix:
                dot.edge(prefix, new_prefix)  # Create an edge between parent and child
            self._add_edges(child_node, dot, new_prefix)
