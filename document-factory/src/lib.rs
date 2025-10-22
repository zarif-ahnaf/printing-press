use js_sys::Array;
use lopdf::{Document, Object};
use std::collections::HashMap;
use wasm_bindgen::JsCast;
use wasm_bindgen::prelude::*;

type ObjectId = (u32, u16);

#[wasm_bindgen]
pub fn merge_pdfs_wasm(pdf_array: &Array) -> Result<Vec<u8>, JsValue> {
    if pdf_array.length() == 0 {
        return Err(JsValue::from_str("Input array is empty"));
    }

    let mut pdf_docs: Vec<Document> = Vec::new();
    for i in 0..pdf_array.length() {
        let val = pdf_array.get(i);
        let uint8_array: &js_sys::Uint8Array = val.dyn_ref().ok_or_else(|| {
            JsValue::from_str(&format!("Item at index {} is not a Uint8Array", i))
        })?;
        let bytes = uint8_array.to_vec();
        let doc = Document::load_mem(&bytes).map_err(|e| {
            JsValue::from_str(&format!("Failed to parse PDF at index {}: {}", i, e))
        })?;
        pdf_docs.push(doc);
    }

    // Start with first document
    let mut merged = pdf_docs.remove(0);
    let mut all_page_refs: Vec<ObjectId> = {
        let pages = merged.get_pages();
        pages.values().copied().collect()
    };

    // Merge remaining documents
    for doc in pdf_docs {
        let mut id_remap: HashMap<ObjectId, ObjectId> = HashMap::new();
        let mut next_id = merged.max_id + 1;

        // Remap all object IDs from this doc
        for &old_id in doc.objects.keys() {
            id_remap.insert(old_id, (next_id, 0));
            next_id += 1;
        }

        // Copy objects with new IDs
        for (&old_id, obj) in &doc.objects {
            let new_id = id_remap[&old_id];
            let new_obj = remap_object(obj, &id_remap)?;
            merged.objects.insert(new_id, new_obj);
        }

        // Collect remapped page IDs
        let pages = doc.get_pages();
        for &page_id in pages.values() {
            if let Some(&new_id) = id_remap.get(&page_id) {
                all_page_refs.push(new_id);
            } else {
                return Err(JsValue::from_str("Page ID not remapped — internal error"));
            }
        }

        merged.max_id = next_id - 1;
    }

    // Rebuild Pages tree
    {
        let catalog = merged
            .catalog_mut()
            .map_err(|_| JsValue::from_str("Failed to get catalog"))?;
        let pages_ref = catalog
            .get(b"Pages")
            .map_err(|_| JsValue::from_str("No /Pages in catalog"))?
            .as_reference()
            .map_err(|_| JsValue::from_str("/Pages is not a reference"))?;

        let pages_obj = merged
            .objects
            .get_mut(&pages_ref)
            .ok_or_else(|| JsValue::from_str("Pages object missing"))?;

        if let Object::Dictionary(pages_dict) = pages_obj {
            pages_dict.set(
                b"Count".to_vec(),
                Object::Integer(all_page_refs.len() as i64),
            );

            let kids_obj = pages_dict
                .get_mut(b"Kids")
                .map_err(|_| JsValue::from_str("No /Kids in Pages"))?;
            let kids_arr = kids_obj
                .as_array_mut()
                .map_err(|_| JsValue::from_str("/Kids is not an array"))?;

            kids_arr.clear();
            for &page_ref in &all_page_refs {
                kids_arr.push(Object::Reference(page_ref));
            }
        } else {
            return Err(JsValue::from_str("Pages object is not a dictionary"));
        }
    }

    let mut output = Vec::new();
    merged
        .save_to(&mut output)
        .map_err(|e| JsValue::from_str(&format!("Serialization failed: {}", e)))?;

    Ok(output)
}

fn remap_object(obj: &Object, id_map: &HashMap<ObjectId, ObjectId>) -> Result<Object, JsValue> {
    match obj {
        Object::Reference(id) => {
            if let Some(&new_id) = id_map.get(id) {
                Ok(Object::Reference(new_id))
            } else {
                Ok(obj.clone())
            }
        }
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
