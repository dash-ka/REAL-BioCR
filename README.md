# REAL-BioCR
Concept Recognition System for Ontology-based Annotations

Let's assume we want to annotate some text with concepts from the Human Phenotype Ontology (HPO), that we pre-indexed in a ChromaDB collection `hp_ontology`.
For our running example, we use the following text:\
_A minimum diagnostic criterion is the combination of either the skin tumours or multiple odontogenic keratocysts plus a positive family history for this disorder._
___
## NER
The NER phase detects spans in text that represent the target entities and return them along with the a short definition, as follows:
```yaml
skin tumors: Abnormal growths or masses that occur in the skin and can be benign or malignant
odontogenic keratocysts: Cysts that develop in the jawbones and are derived from the remnants of dental tissue.
```

___
## Grounding 
For each extracted (and defined) entity we retrieve `k` candidate concepts from the ontology index, using embedding-based search.\
For instance, below is a list the top 3 candidate concepts retrieved for the _skin tumors_ entity.

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
