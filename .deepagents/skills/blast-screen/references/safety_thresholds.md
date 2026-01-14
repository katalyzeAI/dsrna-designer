# EPA Safety Thresholds for dsRNA Off-Target Assessment

## Background

The EPA uses contiguous nucleotide match length as a proxy for off-target
RNAi effects in non-target organisms.

## Thresholds

| Match Length | Risk Level | Recommendation |
|--------------|------------|----------------|
| <15 bp | No significant risk | Safe for use |
| 15-18 bp | Low risk | Flag for review, acceptable |
| ≥19 bp | High risk | Reject candidate |

## Scientific Basis

### Why 19bp?

- siRNAs typically require 19-21bp of complementarity for effective silencing
- Shorter matches (<15bp) rarely trigger RNAi pathway
- 15-18bp may cause transient, weak silencing effects

### Conservative Approach

We use the lower threshold (19bp) rather than 21bp to:
- Provide safety margin for regulatory compliance
- Account for potential secondary siRNA generation
- Protect non-target beneficial insects

## References

1. EPA. "RNAi Technology: Program Formulation for Human Health and Ecological
   Risk Assessment." EPA-HQ-OPP-2013-0485 (2014).

2. Bachman PM, et al. "Characterization of the spectrum of insecticidal activity
   of a double-stranded RNA with targeted activity against Western Corn Rootworm."
   Transgenic Research 22:1207-1222 (2013).

3. Christiaens O, et al. "Double-stranded RNA technology to control insect pests:
   current status and challenges." Frontiers in Plant Science 11:451 (2020).

4. Romeis J, et al. "Assessment of risk of insect-resistant transgenic crops to
   nontarget arthropods." Nature Biotechnology 26:203-208 (2008).

## Implementation Notes

- BLAST with word_size=7 catches short matches
- e-value=10 is permissive to catch weak similarities
- Report maximum alignment length across all hits
- Screen against both human (health) and honeybee (environmental)
