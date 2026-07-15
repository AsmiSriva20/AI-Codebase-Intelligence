print("LOADED VECTORDB")
import chromadb
from app.embeddings import create_embedding

# Persistent ChromaDB (stored on disk)
client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection(
    name="repository"
)


def clear_collection():
    """
    Remove all embeddings from the collection.
    """
    global collection

    client.delete_collection("repository")

    collection = client.get_or_create_collection(
        name="repository"
    )


def store_embeddings(chunks):
    """
    Store embedded chunks in ChromaDB.
    """

    clear_collection()

    for i, chunk in enumerate(chunks):

        collection.add(
            ids=[str(i)],
            documents=[chunk["text"]],
            embeddings=[chunk["embedding"]],
            metadatas=[chunk["metadata"]]
        )

    print("Stored embeddings:", collection.count())


def collection_size():
    """
    Return total number of embeddings.
    """
    return collection.count()


def search_similar(query_embedding, n_results=15):
    """
    Search using an already-created embedding.
    """

    return collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )


def semantic_search(query, n_results=5):
    print("Collection size:", collection.count())

    query_embedding = create_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    print(results)

    return results