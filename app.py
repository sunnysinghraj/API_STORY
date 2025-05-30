from flask import Flask,request,jsonify
from script import process_search_str 
import time
import yaml

with open("config.yml", 'r') as config_file:
    config = yaml.safe_load(config_file)

MAX_QUERY_WORDS = config['MAX_QUERY_WORDS']

app = Flask(__name__)

@app.route('/probable-product',methods=['GET','POST'])
def process():
    start_time = time.time()
    search_str = request.args.get("q", "")
    original_str = search_str
    search_str = search_str.lower().strip()
    if not search_str:
        end_time = time.time()
        time_taken_ms = (end_time - start_time)*1000
        return jsonify({
        "all_ngrams_with_count": [],
        "match_method" : "exact",
        "probable_product": [],
        "original query" : original_str,
        "time_taken_ms": round(time_taken_ms,2)
    })

    if len(search_str.split()) > MAX_QUERY_WORDS:
        end_time = time.time()
        time_taken_ms = (end_time - start_time)*1000
        return jsonify({
        "all_ngrams_with_count": {},
        "match_method" : "exact",
        "probable_product": [],
        "original query" : original_str,
        "time_taken_ms": round(time_taken_ms,2)
    })

    all_ngrams_with_cnt , probable_Product = process_search_str(search_str)
    
    end_time = time.time()
    
    time_taken_ms = (end_time - start_time)*1000
    return jsonify({
        "all_ngrams_with_count": all_ngrams_with_cnt,
        "match_method" : "exact",
        "probable_product": probable_Product,
        "original query" : original_str,
        "time_taken_ms": round(time_taken_ms,2)
    })

#test-function to test whether the api is responsive from varnish end
@app.route("/test",methods=['GET', 'POST'])
def test():
  data = {}
  data['result'] = "OK"
  return jsonify(data)

if __name__ == '__main__' : 
    app.run(debug=True)