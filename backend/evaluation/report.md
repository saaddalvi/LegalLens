# LegalLens evaluation

## Overall (cases: Plain RAG: 35, CRAG: 35)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 80% | 80% |
| Answer accuracy | 63% | 71% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## english (cases: Plain RAG: 14, CRAG: 15)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 71% | 73% |
| Answer accuracy | 57% | 67% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## hindi (cases: Plain RAG: 5, CRAG: 4)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 80% | 75% |
| Answer accuracy | 60% | 50% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## repealed_code (cases: Plain RAG: 6, CRAG: 6)

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
| Answer accuracy | 0% | 40% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | n/a |

## Per case

| Case | Plain RAG | CRAG |
|---|---|---|
| en-const-arrest | wrong, hit (corpus) | wrong, hit (corpus) |
| en-const-speech | correct, hit (corpus) | correct, hit (corpus) |
| en-const-education | correct, hit (corpus) | correct, hit (corpus) |
| en-bns-murder | error (HTTPStatusError) | correct, hit (corpus) |
| en-bns-theft | wrong, miss (corpus) | wrong, miss (corpus_and_fallback) |
| en-bnss-fir | wrong, miss (corpus) | wrong, miss (none) |
| en-bsa-electronic | wrong, miss (corpus) | wrong, miss (corpus) |
| en-cpa-complaint | correct, hit (corpus) | correct, hit (corpus) |
| en-mta-deposit | correct, hit (corpus) | correct, hit (corpus) |
| en-tpa-lease | correct, hit (corpus) | correct, hit (corpus) |
| en-wages-payment | correct, hit (corpus) | correct, hit (corpus) |
| en-wages-overtime | wrong, miss (corpus) | wrong, miss (corpus) |
| en-osh-hours | correct, hit (corpus) | correct, hit (corpus) |
| en-ss-gratuity | correct, hit (corpus) | correct, hit (corpus) |
| en-ir-strike | wrong, hit (corpus) | correct, hit (corpus) |
| hi-const-arrest | wrong, hit (corpus) | wrong, hit (corpus) |
| hi-mta-deposit | correct, hit (corpus) | error (HTTPStatusError) |
| hi-cpa-complaint | correct, hit (corpus) | correct, hit (corpus) |
| hi-wages | wrong, miss (corpus) | wrong, miss (fallback) |
| hi-bns-murder | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-302 | correct, hit (corpus) | correct, hit (corpus) |
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
| poor-rti | wrong (corpus) | correct (fallback) |
| poor-drunk-driving | wrong (corpus) | wrong (none) |
| poor-divorce | wrong (corpus) | wrong (none) |
| poor-dv | wrong (corpus) | correct (fallback) |
| poor-gst | wrong (corpus) | wrong (none) |

2 case runs failed after retries and are excluded from the metrics: en-bns-murder (HTTPStatusError), hi-mta-deposit (HTTPStatusError)
