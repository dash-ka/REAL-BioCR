# REAL-BioCR
Concept Recognition System for Ontology-based Annotations

Let's assume we want to annotate some text with concepts from the Human Phenotype Ontology (HPO) pre-indexed in a ChromaDB collection.\
For our running example, we use the following text:

  _A minimum diagnostic criterion is the combination of either the skin tumours   
  or multiple odontogenic keratocysts plus a positive family history for this disorder._
___
## NER
The NER phase extracts spans that represent target entities from the given text.\
Optionally, for each mention a short definition can be generated.\
Below are the extracted entities and their definitions:
```yaml
skin tumors: Abnormal growths or masses that occur in the skin and can be benign or malignant
odontogenic keratocysts: Cysts that develop in the jawbones and are derived from the remnants of dental tissue.
```

___
## Grounding 
For each extracted entity mention, we first find `k` candidate concepts from the ontology index.\
Below are the top 3 candidate concepts retrieved for the _skin tumors_ entity.

```yaml

candidates:
• ID: HP:0008069
  label: Neoplasm of the skin
  definition: A tumor (abnormal growth of tissue) of the skin.
  synonyms: skin tumors, tumor of the skin, dermatological tumours
  is_a: Neoplasm by anatomical site, Abnormality of the skin

• ID: HP:0000951
  label: Abnormality of the skin
  definition: An abnormality of the skin.
  synonyms: dermatopathy, dermopathy
  is_a: Abnormality of the integument

• ID: HP:0012056,
  label: Cutaneous melanoma
  definition:The presence of a melanoma of skin.
  is_a: melanoma, neoplasm of the skin
```

Then, we use the following prompt to ground each extracted mention using the retieved candidate set:

```text
As an expert clinician, your task is to accurately identify the concept mentioned in the provided text using the concepts listed below. 
Accuracy is paramount. If the text does not precisely refer to any of the concepts listed below, please return "None"; 
otherwise, return the corresponding concept ID in the following format:
answer: <concept ID or None>
confidence: <one of: HIGH, LOW, MEDIUM>

Below are the concepts:
{candidate concept retrieved for a mention}

Text:
{a description of a mention, including label and generated definition}
```
The final output of the system looks like follows:
```yaml

• span: skin tumors
  start: 75
  end: 87
  ID: HP:0008069
  label: Neoplasm of the skin
  confidence: HIGH

• span: odontogenic keratocysts
  start: 100
  end: 124
  ID: HP:0010603
  label:  Odontogenic keratocysts of the jaw
  confidence: HIGH  
```
