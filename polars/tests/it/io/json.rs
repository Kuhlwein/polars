use std::ffi::OsStr;
use std::io::Cursor;

use super::*;

#[test]
fn read_json() {
    let basic_json = r#"{"a":1, "b":2.0, "c":false, "d":"4"}
{"a":-10, "b":-3.5, "c":true, "d":"4"}
{"a":2, "b":0.6, "c":false, "d":"text"}
{"a":1, "b":2.0, "c":false, "d":"4"}
{"a":7, "b":-3.5, "c":true, "d":"4"}
{"a":1, "b":0.6, "c":false, "d":"text"}
{"a":1, "b":2.0, "c":false, "d":"4"}
{"a":5, "b":-3.5, "c":true, "d":"4"}
{"a":1, "b":0.6, "c":false, "d":"text"}
{"a":1, "b":2.0, "c":false, "d":"4"}
{"a":1, "b":-3.5, "c":true, "d":"4"}
{"a":100000000000000, "b":0.6, "c":false, "d":"text"}
"#;
    let file = Cursor::new(basic_json);
    let df = JsonReader::new(file)
        .infer_schema_len(Some(3))
        .with_json_format(JsonFormat::JsonLines)
        .with_batch_size(3)
        .finish()
        .unwrap();
    assert_eq!("a", df.get_columns()[0].name());
    assert_eq!("d", df.get_columns()[3].name());
    assert_eq!((12, 4), df.shape());
}
#[test]
fn read_json_with_whitespace() {
    let basic_json = r#"{   "a":1, "b":2.0, "c"   :false  , "d":"4"}
{"a":-10, "b":-3.5, "c":true, "d":"4"}
{"a":2, "b":0.6, "c":false, "d":"text"   }      
{"a":1, "b":2.0, "c":false, "d":"4"}


{"a":      7, "b":-3.5, "c":true, "d":"4"}
{"a":1, "b":0.6, "c":false, "d":"text"}
{"a":1, "b":2.0, "c":false, "d"  :"4"}
{"a":5, "b":-3.5, "c":true  , "d":"4"}

{"a":1, "b":0.6,   "c":false, "d":"text"}
{"a":1, "b":2.0, "c":false, "d":"4"}
{"a":1, "b":32.5,   "c":false, "d":"99"}
{  "a":100000000000000, "b":0.6, "c":false, "d":"text"}"#;
    let file = Cursor::new(basic_json);
    let df = JsonReader::new(file)
        .infer_schema_len(Some(3))
        .with_json_format(JsonFormat::JsonLines)
        .with_batch_size(3)
        .finish()
        .unwrap();
    assert_eq!("a", df.get_columns()[0].name());
    assert_eq!("d", df.get_columns()[3].name());
    assert_eq!((12, 4), df.shape());
}
#[test]
fn read_json_with_escapes() {
    let escaped_json = r#"{"id": 1, "text": "\""}
    {"text": "\n{\n\t\t\"inner\": \"json\n}\n", "id": 10}
    {"id": 0, "text":"\"","date":"2013-08-03 15:17:23"}
    {"id": 1, "text":"\"123\"","date":"2009-05-19 21:07:53"}
    {"id": 2, "text":"/....","date":"2009-05-19 21:07:53"}
    {"id": 3, "text":"\n\n..","date":"2"}
    {"id": 4, "text":"\"'/\n...","date":"2009-05-19 21:07:53"}
    {"id": 5, "text":".h\"h1hh\\21hi1e2emm...","date":"2009-05-19 21:07:53"}
    {"id": 6, "text":"xxxx....","date":"2009-05-19 21:07:53"}
    {"id": 7, "text":".\"quoted text\".","date":"2009-05-19 21:07:53"}
    
"#;
    let file = Cursor::new(escaped_json);
    let df = JsonLineReader::new(file)
        .infer_schema_len(Some(6))
        .finish()
        .unwrap();
    assert_eq!("id", df.get_columns()[0].name());
    assert_eq!(AnyValue::Utf8("\""), df.column("text").unwrap().get(0));
    assert_eq!("text", df.get_columns()[1].name());
    assert_eq!((10, 3), df.shape());
}

#[test]
fn read_unordered_json() {
    let unordered_json = r#"{"a":1, "b":2.0, "c":false, "d":"4"}
{"a":-10, "b":-3.5, "c":true, "d":"4"}
{"a":2, "b":0.6, "c":false, "d":"text"}
{"a":1, "b":2.0, "c":false, "d":"4"}
{"a":7, "b":-3.5, "c":true, "d":"4"}
{"a":1, "b":0.6, "c":false, "d":"text"}
{"d":1, "c":false, "d":"4", "b":2.0}
{"b":-3.5, "c":true, "d":"4", "a":5}
{"d":"text", "a":1, "c":false, "b":0.6}
{"a":1, "b":2.0, "c":false, "d":"4"}
{"a":1, "b":-3.5, "c":true, "d":"4"}
{"a":100000000000000, "b":0.6, "c":false, "d":"text"}
"#;
    let file = Cursor::new(unordered_json);
    let df = JsonReader::new(file)
        .infer_schema_len(Some(3))
        .with_json_format(JsonFormat::JsonLines)
        .with_batch_size(3)
        .finish()
        .unwrap();
    assert_eq!("a", df.get_columns()[0].name());
    assert_eq!("d", df.get_columns()[3].name());
    assert_eq!((12, 4), df.shape());
}
