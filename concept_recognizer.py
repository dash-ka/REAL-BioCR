from openai import OpenAI
import logging, re, yaml
from collections import defaultdict

# Open the log file in write mode to empty its contents
with open('logging.log', 'w'):
    pass

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename='logging.log', level=logging.INFO)
logger = logging.getLogger(__name__)



CONCEPT_PROMPT = 'As a clinical expert, write a single sentence definition that explains the meaning of the concept:'

DEFINE_PROMPT = 'Given a text and a semicolon-separated list of entities from that text, write a definition for each entity in the following format:\n'\
'entity: <A single sentence definition that explains the meaning of the entity>'

GROUNDING_PROMPT = 'As an expert clinician, your task is to accurately identify the concept mentioned in the provided text using the concepts listed below. '\
'Accuracy is paramount. If the text does not precisely refer to any of the concepts listed below, please return "None"; '\
'otherwise, return the corresponding concept ID in the following format:\n'\
'answer: <concept ID or None>\n'\
'confidence: <one of: HIGH, LOW, MEDIUM>\n'

client = OpenAI()
class Lumus:

    def __init__(self, generative_model, embedding_model, indexer):
        self.generative_model = generative_model
        self.embedding_model = embedding_model
        self.si = indexer
        self.terminology = {}

    def init_vocab(self, collection):
        for term in self.si.client.get_collection(collection).get(include=["metadatas"])["metadatas"]:
            self.terminology[term["label"].lower()] = term["id"]
            if syns:= term.get("synonyms", ""):
                for syn in syns.split(", "):
                    self.terminology[syn.lower()] = term["id"]


    def prompt(self, text, system, model=None):
        if model is None:
            model = self.generative_model
        
        logger.info(f"Using model: {model}")
        response = client.chat.completions.create(
                model=model,
                messages=[
                    {'role': 'system',
                     'content': system},
                    {'role': 'user',
                     'content': text}
                ],
                temperature=0
            )
        return response.choices[0].message.content
    


    def gen_definition(self, concept):
        return self.prompt(text=concept, system=CONCEPT_PROMPT)
    
    def gen_grounding_prompt(self, mention, concepts, linking_fields=None, examples=None):

        system_prompt = GROUNDING_PROMPT
        if examples:
            system_prompt += f'Here are some examples:\n' + "\n".join(examples)+ '\n'

        if linking_fields is None:
            linking_fields = ("label", "definition")
        
        _candidates = []
        for concept in concepts:
                _candidates.append(f'ID: {concept["ID"]}')
                _candidates.append(self.si.get_description(concept, linking_fields) + "\n")

        system_prompt += 'Below are the concepts:\n\n' +  "\n".join(f'{c}' for c in _candidates)
        mentions = f'\n\n[Text]\n{self.si.get_description(mention, fields=linking_fields)}'    
        return {"mention_to_ground": mentions, "prompt": system_prompt}
    
    
    def grab_candidates(self, mentions, k, collection, fields=None, with_backup=False):

        def find_exact(input_string, vocab):

            source_string = ' '.join(f'<{item.strip()}>' for item in vocab)
            pattern = f"<{input_string.lower()}>"
            result = ""
            match = re.search(pattern, source_string)
            if match:
                result = vocab[match.group(0).strip('<>')]
            return result
        
        knn = self.si.search_concepts(
                queries=mentions,
                k_neighbors=k,
                collection=collection,
                fields=fields,
                model=self.embedding_model
            ) 
        
        logger.info(f"Retrieved set of {k} candidates for {len(mentions)} mentions: {knn}")
        
        for m in range(len(mentions)):
            concepts = []
            for n in range(k):
                candidate = knn["metadatas"][m][n]
                concepts.append(candidate)                    
            
            if with_backup:
                logger.info(f"Applying backup.")
                if not self.terminology:
                    self.init_vocab(collection)

                candidates = [c["id"] for c in concepts]
                exact_match = find_exact(mentions[m]["label"], self.terminology)
                
                if exact_match:
                    if exact_match in candidates: 
                        logger.info(f"Inserting the exact match (" + str(exact_match) + ") for the term: " + mentions[m]["label"])
                        mentions[m]["few_shot"] = {"id":exact_match, "confidence":"HIGH", "exact":True} 
                    else:
                        term_meta = self.si.client.get_collection(collection).get(ids = [exact_match])["metadatas"][0]
                        concepts.insert(0, {k:v for k, v in term_meta.items() if v})

            mentions[m]["concepts"] = concepts
            
        return mentions
    

    def ground(self, mentions, collection, k, embedding_fields=None, linking_fields=None, examples=None, confidence=("HIGH"), model=None, with_backup=False):
        
        # grab candidates for each mention from knowledge source
        logger.info(f"Retrieving {k} candidates for mentions:\n {mentions}")
        mentions = self.grab_candidates(
                    mentions, k=k, 
                    collection=collection, 
                    fields=embedding_fields,
                    with_backup=with_backup
                    )
        
        results = [] 
        for m in mentions:
            if with_backup and m.get("few_shot"):
                logger.info(f"EXACT MATCH, NO GROUNDING FOR:\n {m}" )
                # dont't ground if an exact match has been found
                results.append(m) 

            else:
                pr = self.gen_grounding_prompt(
                            mention=m, 
                            concepts=[{k:c.get(k) for k in ["ID", "label", "definition", "synonyms"] if k in c} for c in m["concepts"]],
                            examples=examples,
                            linking_fields=linking_fields)
            
                response = self.prompt(pr["mention_to_ground"], system=pr["prompt"], model=model)
                logger.info(f'prompting with: {pr["prompt"]}')
                logger.info(f'mentions_to_ground: {pr["mention_to_ground"]}')
                logger.info(f"Response: {response} ")

                uri = re.findall("(?<=answer: )[^\n]+", response)
                conf = re.findall("(?<=confidence: )[A-Z]+", response)
                if uri and conf and (conf[0] in confidence) and ("none" not in uri[0].lower()):
                    results.append(m | {"few_shot" : {"id":uri[0], "confidence":conf[0]}}) 
                else: 
                    results.append(m) 
        return results


    def extract(
            self,
            text,
            categories,
            define=False,
            model=None
            ):      

        # build extract prompt 
        system_prompt = 'From the text below, extract all mentions of the following entities in the following format:\n\n' 
        system_prompt += categories[0] + ' It must be semicolon-separated. If no mention of ' + categories[0].split(":")[0] + ' is found in text, respond None.>'
        system_prompt += "\n\nText:\n"
            
        # extract mentions
        logger.info(f"Input text: {text}")
        logger.info(f"Prompting with: {system_prompt}")
        mentions = self.prompt(text, system=system_prompt, model=model)

        logger.info(f"Extracted mentions: {mentions}")
        mentions = mentions.split(":", 1)[-1].strip().split(";")
        mentions = [m.strip() for m in mentions if m.strip() and "none" not in m.lower()] # ordered list of mentions

        parsed_mentions = []
        if not mentions:
            logger.info(f"No mention found !")

        else:
            if define:
                # define all extracted mentions at once
                instruction = f'\nHere is the text:\n{text}\nHere is the list of entities:\n{", ".join(mentions)}'
                defined_mentions = self.prompt(instruction, system=DEFINE_PROMPT, model=model)
                logger.info(f"Defined mentions: {mentions}")

                for mention in defined_mentions.split("\n"):
                    if ":" in mention.strip():
                        toks = mention.strip().split(":") 
                        label, definition = toks[0].strip(), toks[1].strip()

                        if len(toks) > 2:
                            logger.info("Warning: more than one ':' in one line {mention}")
                        parsed_mentions.append({"label":label, "definition": definition})

            else:
                for mention in mentions:
                    label = mention.strip()
                    parsed_mentions.append({"label":label})
        
        return parsed_mentions