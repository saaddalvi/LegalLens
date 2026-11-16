# 07: Hindi Queries and answers

**What to build:** The Query language is detected automatically. A Hindi Query retrieves relevant English Provisions through multilingual embeddings and gets a Hindi answer, while each Citation quotes the original English text verbatim.

**Blocked by:** 03

**Status:** done

- [x] Endpoint test: a Hindi Query about a constitutional right retrieves the expected Article
- [x] Endpoint test: the answer language is Hindi and the Citation text is the unchanged English Provision
- [x] Endpoint test: an English Query still gets an English answer
- [x] The response reports the detected answer language
- [x] The frontend renders Hindi text correctly
