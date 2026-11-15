# 07: Hindi Queries and answers

**What to build:** The Query language is detected automatically. A Hindi Query retrieves relevant English Provisions through multilingual embeddings and gets a Hindi answer, while each Citation quotes the original English text verbatim.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Endpoint test: a Hindi Query about a constitutional right retrieves the expected Article
- [ ] Endpoint test: the answer language is Hindi and the Citation text is the unchanged English Provision
- [ ] Endpoint test: an English Query still gets an English answer
- [ ] The response reports the detected answer language
- [ ] The frontend renders Hindi text correctly
