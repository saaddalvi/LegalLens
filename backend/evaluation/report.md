# LegalLens evaluation

## Overall (cases: Plain RAG: 36, CRAG: 33)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 96% | 91% |
| Answer accuracy | 86% | 97% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## english (cases: Plain RAG: 15, CRAG: 13)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 100% | 92% |
| Answer accuracy | 100% | 100% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## hindi (cases: Plain RAG: 5, CRAG: 5)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 80% | 80% |
| Answer accuracy | 100% | 100% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## repealed_code (cases: Plain RAG: 6, CRAG: 5)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 100% | 100% |
| Answer accuracy | 100% | 100% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## out_of_scope (cases: Plain RAG: 5, CRAG: 5)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | n/a | n/a |
| Answer accuracy | 100% | 100% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | n/a | n/a |

## poor_retrieval (cases: Plain RAG: 5, CRAG: 5)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | n/a | n/a |
| Answer accuracy | 0% | 80% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## Per case

| Case | Plain RAG | CRAG |
|---|---|---|
| en-const-arrest | correct, hit (corpus) | correct, hit (corpus) |
| en-const-speech | correct, hit (corpus) | correct, hit (corpus) |
| en-const-education | correct, hit (corpus) | correct, hit (corpus) |
| en-bns-murder | correct, hit (corpus) | correct, hit (corpus) |
| en-bns-theft | correct, hit (corpus) | correct, hit (corpus) |
| en-bnss-fir | correct, hit (corpus) | correct, hit (corpus) |
| en-bsa-electronic | correct, hit (corpus) | correct, hit (corpus) |
| en-cpa-complaint | correct, hit (corpus) | correct, hit (corpus) |
| en-mta-deposit | correct, hit (corpus) | error (HTTPStatusError) |
| en-tpa-lease | correct, hit (corpus) | correct, hit (corpus) |
| en-wages-payment | correct, hit (corpus) | correct, hit (corpus) |
| en-wages-overtime | correct, hit (corpus) | error (HTTPStatusError) |
| en-osh-hours | correct, hit (corpus) | correct, hit (corpus) |
| en-ss-gratuity | correct, hit (corpus) | correct, hit (corpus) |
| en-ir-strike | correct, hit (corpus) | correct, miss (fallback) |
| hi-const-arrest | correct, hit (corpus) | correct, hit (corpus) |
| hi-mta-deposit | correct, miss (corpus) | correct, miss (corpus) |
| hi-cpa-complaint | correct, hit (corpus) | correct, hit (corpus) |
| hi-wages | correct, hit (corpus) | correct, hit (corpus) |
| hi-bns-murder | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-302 | correct, hit (corpus) | error (HTTPStatusError) |
| rep-ipc-420 | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-498a | correct, hit (corpus) | correct, hit (corpus) |
| rep-crpc-154 | correct, hit (corpus) | correct, hit (corpus) |
| rep-crpc-41 | correct, hit (corpus) | correct, hit (corpus) |
| rep-iea-65b | correct, hit (corpus) | correct, hit (corpus) |
| oos-sue | correct (corpus) | correct (corpus) |
| oos-sign | correct (corpus) | correct (corpus) |
| oos-us-law | correct (corpus) | correct (corpus) |
| oos-recipe | correct (corpus) | correct (corpus) |
| oos-plead | correct (corpus) | correct (corpus) |
| poor-rti | wrong (corpus) | wrong (fallback) |
| poor-drunk-driving | wrong (corpus) | correct (corpus_and_fallback) |
| poor-divorce | wrong (corpus) | correct (fallback) |
| poor-dv | wrong (corpus) | correct (fallback) |
| poor-gst | wrong (corpus) | correct (fallback) |

3 case runs failed after retries and are excluded from the metrics: en-mta-deposit (HTTPStatusError), en-wages-overtime (HTTPStatusError), rep-ipc-302 (HTTPStatusError)
