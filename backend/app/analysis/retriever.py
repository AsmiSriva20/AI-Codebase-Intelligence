from app.config import SEARCH_DEFAULT_N_RESULTS


def filter_results(results, max_results=SEARCH_DEFAULT_N_RESULTS):

    unique = set()
    filtered = []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    for doc, meta in zip(documents, metadatas):

        key = (meta["path"], meta["name"])

        if key in unique:
            continue

        unique.add(key)

        filtered.append({
            "text": doc,
            "metadata": meta
        })

        if len(filtered) == max_results:
            break

    return filtered