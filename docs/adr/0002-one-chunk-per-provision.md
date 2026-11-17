# One Chunk per Provision

Each Section or Article is a single Chunk, rather than a fixed-size token window, so a Citation maps exactly to one retrievable unit and the Hallucinated-citation check can be exact. This costs a per-Act parser, since Acts are structured differently, and very long Provisions become large Chunks.

## Amendment: long Provisions are stored as several pieces

The embedding model reads only about 512 tokens, so a long Provision (BNS 303 is 5.9 KB) was matched on its opening alone and a plain-language Query could not reach the part that answered it. A Provision longer than 800 characters is now split at line ends into pieces, each embedded separately. Search scores a Provision by its best piece. A Provision is still one unit everywhere else: the Corpus returns whole Provisions, one Citation maps to one Provision, and the Hallucinated-citation check is unchanged. Measured on the golden set, the expected Provision lands in the top 10 for 20 of 26 cases, up from 18 (larger embedding models, a hybrid search and the Act name in the chunk text did not beat 18).

