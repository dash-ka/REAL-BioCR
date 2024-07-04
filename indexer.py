from dataclasses import dataclass, field
from typing import Iterable, List
from chromadb import ClientAPI as API
from chromadb.api import EmbeddingFunction
from chromadb.utils import embedding_functions #import OllamaEmbeddingFunction, OpenAIEmbeddingFunction
from chromadb import Settings
import chromadb, os, logging , yaml, json
from oaklib.utilities.iterator_utils import chunk
from time import time
from tqdm.notebook import tqdm

for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
logging.basicConfig(filename='logging.log', level=logging.INFO)
logger = logging.getLogger(__name__)


class SemanticIndex():
        
    @staticmethod
    def get_description(metadata, fields=None):
       
        if fields is None:
            if isinstance(metadata, dict):
                    return yaml.safe_dump({k: v for k, v in metadata.items() if v}, sort_keys=False).strip()
            if isinstance(metadata, str):
                    return metadata
            
        elif isinstance(fields, (list, set, tuple)):
            return yaml.safe_dump({k: v for k, v in metadata.items() if k in fields and v}, sort_keys=False).strip()
        elif isinstance(fields, str) and isinstance(metadata, dict):
            return metadata[fields]
    
    def __init__(self, path=None, model=None, metadata=None):

        if model is None:
            self.model = "all-MiniLM-L6-v2" 
        else:
            self.model = model

        if metadata is None:
            self.metadata =  {"hnsw:space": "cosine"} 
        else:
            self.metadata = metadata

        if path is None:
            self.path = "./db"
        else:
            self.path = path

        self.client = chromadb.PersistentClient(
                path=str(self.path), 
                settings=Settings(allow_reset=False, anonymized_telemetry=False)
            )
        logger.info(f"Creating new PersistendClient at {self.path} with model: {self.model}, metadata: {self.metadata}")

    def _object_metadata(self, obj):

        _obj = {k: v for k, v in obj.items() if not isinstance(v, (dict, list, type)) and v}
        _obj["ID"] = _obj.get("id", "")
        #_obj["_json"] = json.dumps(_obj)
        return _obj

    def _embedding_function(self, model: str = None) -> EmbeddingFunction:
        """
        Get the embedding function for a given model.

        :param model:
        :return:
        """
        if model is None:
            raise ValueError("Model must be specified")
        
        if model.startswith("openai:"):
            logger.info(f'Using openai model {"text-embedding-ada-002"}')
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.environ.get("OPENAI_API_KEY"),
                model_name="text-embedding-ada-002",
            )

        elif model.startswith("llama:"):
            logger.info(f'Using llama model {"nomic-embed-text"}') #model.lstrip("^llama:")
            return embedding_functions.OllamaEmbeddingFunction(
                url="http://localhost:11434/api/embeddings",
                #model_name=model.lstrip("^llama:")
                model_name="nomic-embed-text"
            )     
             
        else:
            logger.info(f"Using default model")
            return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=self.model)


    def _get_or_create_collection(self, collection, model=None, metadata=None):
   
        if model is None:
            model = self.model
        if metadata is None:
            metadata = self.metadata | {"model":model}

        ef = self._embedding_function(model) # must supply embedding function if when getting a collection
        return self.client.get_or_create_collection(
            name=collection,
            embedding_function=ef,
            metadata=metadata)


    def add_concepts(self, concepts, collection, fields=None, model=None, metadata=None):

        logger.info(f"Creating or getting collection {collection}")
        collection = self._get_or_create_collection(collection, model=model, metadata=metadata)
         
        logger.info(f"Inserting {len(concepts)} objects into {collection.name}")
        start = time()
        for id, meta in tqdm(concepts.items()):
            collection.add(
                documents = [self.get_description(meta, fields=fields)],
                metadatas = [self._object_metadata(meta)],#[meta],
                ids = [id]
                )
        logger.info(f"Time for stream indexing: {time()-start}")


    def add_batch(self, concepts, collection, fields=None, batch_size=None, model=None, metadata=None):

        """
        concepts : List[Dict]
        collection : str
        fields : Iterable[str]
        batch_size : int
        model : str 
        metadata : dict
        """
        
        if batch_size is None:
            batch_size = 500

        logger.info(f"Creating or getting collection {collection}")
        collection = self._get_or_create_collection(collection, model=model, metadata=metadata)
                
        logger.info(f"Inserting batches of {len(concepts)} objects into {collection.name}")
        start = time()
        for next_chunk in tqdm(chunk(concepts, batch_size)):
            
            next_chunk = list(next_chunk)
            logger.info(f"Indexing another batch of size {len(next_chunk)}")
            logger.info(f"Item  {next_chunk[0]}")
            documents = [self.get_description(o, fields) for o in next_chunk]
            metadatas = [self._object_metadata(o) for o in next_chunk]
            logger.info(f"Document  {documents[0]}")
            ids = [str(o["id"]) for o in next_chunk]
            collection.add(
                documents = documents,
                metadatas = metadatas,
                ids = ids
                )
        logger.info(f"Time for batch indexing: {time()-start}")



    def search_concepts(self, queries, collection, k_neighbors, where=None, fields=None, model=None, metadata=None):        
        if not isinstance(queries, list):
            queries = [queries]

        logger.info(
            f'Query texts: {[self.get_description(q, fields=fields) for q in queries]} \nwhere: {where} include: {"metadatas, distances"}, fields={fields}, model={model}'
        )
        collection = self._get_or_create_collection(collection, model=model, metadata=metadata)
        logger.info(f'Using collection {collection.name} with metadata:{collection.metadata}')
        return collection.query(
            query_texts=[self.get_description(q, fields=fields) for q in queries], 
            n_results=k_neighbors,
            where=where,
            include=["metadatas", "distances", "documents"]
        )