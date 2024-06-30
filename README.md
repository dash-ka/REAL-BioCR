# REAL-BioCR
Concept Recognition System for Ontology-based Annotations

Let's assume we want to annotate some text with concepts from the Human Phenotype Ontology (HPO), that we pre-indexed in a ChromaDB collection `hp_ontology`.
For our running example, we use the following text:
_A minimum diagnostic criterion is the combination of either the [skin tumours] or multiple [odontogenic keratocysts] plus a positive family history for this disorder._
___
## NER
The NER phases uses the following prompt to extract spans representing phenotypic features:
`From the text below, extract all mentions of the following entities in the following format: 
phenotypes: < a semicolon-separated list of human phenotypes, including physical abnormalities, symptoms of disease and inherited disorders. It must be semicolon separated.>`
Which produced the following list of spans:
```yaml
phenotypes: skin tumors;  odontogenic keratocysts
Then, we generate a short definition for each extracted entity using the following prompt:

`Given a text and a semicolon-separated list of entities from that text, write a definition for each entity in the following format:\n'\
'entity: <A single sentence definition that explains the meaning of the entity>`


```yaml

candidates:
• ID: HP:0008069
  name: Neoplasm of the skin
  definition: A tumor (abnormal growth of tissue) of the skin.
  synonyms: skin tumors, tumor of the skin, dermatological tumours, tumour of the skin
  is_a: Neoplasm by anatomical site, Abnormality of the skin

• ID: HP:0000951
  name: Abnormality of the skin
  definition: An abnormality of the skin.
  synonyms: dermatopathy, dermopathy
  is_a: Abnormality of the integument

• ID: HP:0012056,
  name: Cutaneous melanoma
  definition:The presence of a melanoma of skin.
  is_a: melanoma, neoplasm of the skin
