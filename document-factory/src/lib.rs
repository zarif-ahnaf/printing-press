use js_sys::Array;
use lopdf::{Document, Object, Stream};
use std::collections::HashMap;
use wasm_bindgen::prelude::*;

type ObjectId = (u32, u16);

#[wasm_bindgen]
pub fn merge_pdfs_wasm(pdf_array: &Array) -> Result<Vec<u8>, JsValue> {
    if pdf_array.length() == 0 {
        return Err(JsValue::from_str("Input array is empty"));
    }

    // Pre-allocate with capacity
    let mut pdf_docs = Vec::with_capacity(pdf_array.length() as usize);

    // Load all PDFs with error context
    for i in 0..pdf_array.length() {
        let val = pdf_array.get(i);
        let uint8_array: &js_sys::Uint8Array = val
            .dyn_ref()
            .ok_or_else(|| JsValue::from_str(&format!("Item {} is not Uint8Array", i)))?;

        let bytes = uint8_array.to_vec();
        let doc = match Document::load_mem(&bytes) {
            Ok(doc) => doc,
            Err(e) => {
                // Try with ignore_corrupt (lopdf v0.32+)
                #[cfg(feature = "nom")]
                {
                    Document::load_mem_with_options(
                        &bytes,
                        lopdf::ParseOptions {
                            ignore_corrupt: true,
                        },
                    )
                    .map_err(|_| {
                        JsValue::from_str(&format!("PDF {} corrupt/unparseable: {}", i, e))
                    })?
                }
                #[cfg(not(feature = "nom"))]
                {
                    return Err(JsValue::from_str(&format!("PDF {} parse error: {}", i, e)));
                }
            }
        };

        // Check for unsupported features
        if has_object_streams(&doc) {
            return Err(JsValue::from_str(&format!(
                "PDF {} uses object streams (unsupported by lopdf)",
                i
            )));
        }

        pdf_docs.push(doc);
    }

    let mut merged = pdf_docs.remove(0);
    let mut all_page_refs = get_all_page_refs(&merged)?;

    for doc in pdf_docs {
        let page_refs = get_all_page_refs(&doc)?;
        if page_refs.is_empty() {
            continue; // Skip empty docs
        }

        let mut id_remap: HashMap<ObjectId, ObjectId> = HashMap::new();
        let mut next_id = merged.max_id + 1;

        // Remap all object IDs
        for &old_id in doc.objects.keys() {
            id_remap.insert(old_id, (next_id, 0));
            next_id += 1;
        }

        // Copy objects with ID remapping
        for (&old_id, obj) in &doc.objects {
            let new_id = id_remap[&old_id];
            let new_obj = remap_object(obj, &id_remap)
                .map_err(|e| JsValue::from_str(&format!("Remap failed: {:?}", e)))?;
            merged.objects.insert(new_id, new_obj);
        }

        // Remap page refs
        for &page_id in &page_refs {
            if let Some(&new_id) = id_remap.get(&page_id) {
                all_page_refs.push(new_id);
            } else {
                return Err(JsValue::from_str("Page ID not remapped"));
            }
        }

        merged.max_id = next_id - 1;
    }

    // Rebuild Pages tree as flat list (simplest approach)
    rebuild_pages_tree(&mut merged, all_page_refs)
        .map_err(|e| JsValue::from_str(&format!("Pages tree rebuild failed: {}", e)))?;

    let mut output = Vec::new();
    merged
        .save_to(&mut output)
        .map_err(|e| JsValue::from_str(&format!("Serialization failed: {}", e)))?;

    Ok(output)
}

fn has_object_streams(doc: &Document) -> bool {
    doc.objects.values().any(|obj| {
        matches!(obj, Object::Stream(Stream { dict, .. }) if dict.get(b"Type").is_ok_and(|o| o == &Object::Name(b"ObjStm".to_vec())))
    })
}

fn get_all_page_refs(doc: &Document) -> Result<Vec<ObjectId>, JsValue> {
    let pages = doc.get_pages();
    Ok(pages.values().copied().collect())
}

fn rebuild_pages_tree(
    doc: &mut Document,
    page_refs: Vec<ObjectId>,
) -> Result<(), Box<dyn std::error::Error>> {
    let catalog = doc.catalog_mut()?;
    let pages_ref = catalog.get(b"Pages")?.as_reference()?;

    let pages_obj = doc.objects.get_mut(&pages_ref).unwrap();
    if let Object::Dictionary(dict) = pages_obj {
        dict.set(b"Count".to_vec(), Object::Integer(page_refs.len() as i64));
        let kids = dict.get_mut(b"Kids")?.as_array_mut()?;
        kids.clear();
        for &page_ref in &page_refs {
            kids.push(Object::Reference(page_ref));
        }
    }
    Ok(())
}

fn remap_object(
    obj: &Object,
    id_map: &HashMap<ObjectId, ObjectId>,
) -> Result<Object, Box<dyn std::error::Error>> {
    match obj {
        Object::Reference(id) => Ok(Object::Reference(*id_map.get(id).unwrap_or(id))),
        Object::Array(arr) => {
            let mut new_arr = Vec::with_capacity(arr.len());
            for item in arr {
                new_arr.push(remap_object(item, id_map)?);
            }
            Ok(Object::Array(new_arr))
        }
        Object::Dictionary(dict) => {
            let mut new_dict = lopdf::Dictionary::new();
            for (key, value) in dict.iter() {
                new_dict.set(key.clone(), remap_object(value, id_map)?);
            }
            Ok(Object::Dictionary(new_dict))
        }
        _ => Ok(obj.clone()),
    }
}
