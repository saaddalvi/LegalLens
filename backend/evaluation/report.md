# LegalLens evaluation

## Overall (32 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 68% | 67% |
| Answer accuracy | 62% | 68% |
| Citation validity | 100% | 100% |

## english (13 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 54% | 54% |
| Answer accuracy | 54% | 54% |
| Citation validity | 100% | 100% |

## hindi (4 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 75% | 60% |
| Answer accuracy | 75% | 60% |
| Citation validity | 100% | 100% |

## repealed_code (5 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 100% | 100% |
| Answer accuracy | 100% | 100% |
| Citation validity | 100% | 100% |

## out_of_scope (5 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | n/a | n/a |
| Answer accuracy | 100% | 100% |
| Citation validity | 100% | 100% |

## poor_retrieval (5 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | n/a | n/a |
| Answer accuracy | 0% | 40% |
| Citation validity | 100% | 100% |

## Per case

| Case | Plain RAG | CRAG |
|---|---|---|
| en-const-arrest | wrong, miss (corpus) | error (HTTPStatusError) |
| en-const-speech | correct, hit (corpus) | correct, hit (corpus) |
| en-const-education | correct, hit (corpus) | correct, hit (corpus) |
| en-bns-murder | correct, hit (corpus) | correct, hit (corpus) |
| en-bns-theft | wrong, miss (corpus) | wrong, miss (corpus) |
| en-bnss-fir | wrong, miss (corpus) | wrong, miss (fallback) |
| en-bsa-electronic | error (HTTPStatusError) | wrong, miss (corpus) |
| en-cpa-complaint | correct, hit (corpus) | correct, hit (corpus) |
| en-mta-deposit | correct, hit (corpus) | correct, hit (corpus) |
| en-tpa-lease | error (HTTPStatusError) | correct, hit (corpus) |
| en-wages-payment | wrong, miss (corpus) | wrong, miss (fallback) |
| en-wages-overtime | wrong, miss (corpus) | wrong, miss (corpus) |
| en-osh-hours | wrong, miss (corpus) | wrong, miss (corpus) |
| en-ss-gratuity | correct, hit (corpus) | error (HTTPStatusError) |
| en-ir-strike | correct, hit (corpus) | correct, hit (corpus) |
| hi-const-arrest | error (HTTPStatusError) | wrong, miss (corpus) |
| hi-mta-deposit | correct, hit (corpus) | correct, hit (corpus) |
| hi-cpa-complaint | correct, hit (corpus) | correct, hit (corpus) |
| hi-wages | wrong, miss (corpus) | wrong, miss (fallback) |
| hi-bns-murder | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-302 | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-420 | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-498a | correct, hit (corpus) | correct, hit (corpus) |
| rep-crpc-154 | error (HTTPStatusError) | correct, hit (corpus) |
| rep-crpc-41 | correct, hit (corpus) | correct, hit (corpus) |
| rep-iea-65b | correct, hit (corpus) | correct, hit (corpus) |
| oos-sue | correct (corpus) | correct (corpus) |
| oos-sign | correct (corpus) | correct (corpus) |
| oos-us-law | correct (corpus) | correct (corpus) |
| oos-recipe | correct (corpus) | correct (corpus) |
| oos-plead | correct (corpus) | correct (corpus) |
| poor-rti | wrong (corpus) | correct (fallback) |
| poor-drunk-driving | wrong (corpus) | wrong (corpus) |
| poor-divorce | wrong (corpus) | wrong (fallback) |
| poor-dv | wrong (corpus) | wrong (fallback) |
| poor-gst | wrong (corpus) | correct (fallback) |

6 case runs failed after retries and are excluded from the metrics: en-bsa-electronic (HTTPStatusError), en-tpa-lease (HTTPStatusError), hi-const-arrest (HTTPStatusError), rep-crpc-154 (HTTPStatusError), en-const-arrest (HTTPStatusError), en-ss-gratuity (HTTPStatusError)
