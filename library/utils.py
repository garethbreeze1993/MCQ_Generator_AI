def get_final_id(num: str):
    n = num.split('id')
    try:
        x = n[-1]
        fin = int(x)
    except Exception:
        return False
    else:
        return fin


def get_lists_for_chroma_upsert(all_splits: list, new_id: int):

    id_list = []
    page_content_list = []
    metadata_list = []

    for split in all_splits:
        id_list.append(f'id{new_id}')
        page_content_list.append(split.page_content)
        metadata_list.append(split.metadata)
        new_id += 1

    return id_list, page_content_list, metadata_list


def get_list_of_ids_for_chroma_deletion(start_id: int, end_id: int):

    list_of_ids = [f"id{i}" for i in range(start_id, end_id + 1)]

    return list_of_ids