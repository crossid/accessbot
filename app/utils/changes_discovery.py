def discover_document_changes(existing_docs, new_texts, new_metadata, new_ids):
    """
    Discovers changes between existing and new documents.
    Returns tuple of (docs_to_delete, texts_to_insert, metadata_to_insert, ids_to_insert)
    """
    existing_doc_dict = {doc.custom_id: doc.document for doc in existing_docs}

    docs_to_delete = []
    metadata_to_insert = []
    ids_to_insert = []
    texts_to_insert = []

    # Find new and changed documents
    for i, doc_id in enumerate(new_ids):
        if doc_id not in existing_doc_dict:
            # New document
            texts_to_insert.append(new_texts[i])
            metadata_to_insert.append(new_metadata[i])
            ids_to_insert.append(doc_id)
        elif existing_doc_dict[doc_id] != new_texts[i]:
            # Changed document
            docs_to_delete.append(doc_id)
            texts_to_insert.append(new_texts[i])
            metadata_to_insert.append(new_metadata[i])
            ids_to_insert.append(doc_id)

    # Find deleted documents
    docs_to_delete_not_exist = set(existing_doc_dict.keys()) - set(new_ids)
    docs_to_delete.extend(docs_to_delete_not_exist)

    return (docs_to_delete, texts_to_insert, metadata_to_insert, ids_to_insert)
