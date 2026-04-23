import type { CorpusDocument } from "../types";

export const corpusDocuments: CorpusDocument[] = [
  {
    id: "23173_1_fully_executed_agreement_with_exhibits__870df94e",
    title: "Tyler Technologies master agreement",
    sourceFilename: "23173_1_fully_executed_agreement_with_exhibits.pdf",
    overview:
      "Executed governing agreement for enterprise software and related services, with enough structure to answer base-state questions directly from domain notes.",
    procurement: {
      buyer: "Lake County, Illinois",
      seller: "Tyler Technologies, Inc.",
      subject: "Enterprise software implementation and support services",
      category: "software_it",
      summary:
        "County purchase of software licensing, implementation, and ongoing support from Tyler Technologies.",
    },
    classification: {
      procurementStage: "contracting",
      primaryDocumentRole: "operative",
      confidence: 0.96,
    },
    documentMapType: "governing",
    governingNotes: {
      identity: [
        {
          label: "What this document is",
          answer:
            "A fully executed master services agreement with exhibits covering software licensing, implementation services, and support obligations.",
          citations: [
            {
              pageNumber: 1,
              snippet: "This Agreement is entered into by and between Lake County and Tyler Technologies, Inc.",
            },
          ],
        },
        {
          label: "Linked documents or materials",
          answer:
            "The agreement incorporates attached exhibits for pricing, scope, and support terms.",
          citations: [
            {
              pageNumber: 2,
              snippet: "The attached exhibits are incorporated and form part of this Agreement.",
            },
          ],
        },
      ],
      parties: [
        {
          label: "Who the main parties are",
          answer:
            "Lake County is the public contracting party and Tyler Technologies, Inc. is the counterparty vendor.",
          citations: [
            {
              pageNumber: 1,
              snippet: "Lake County, Illinois ... and Tyler Technologies, Inc.",
            },
          ],
        },
      ],
      subject: [
        {
          label: "What is being bought or governed",
          answer:
            "Software licensing, implementation, training, and support for a county records and operations platform.",
          citations: [
            {
              pageNumber: 3,
              snippet: "Tyler shall provide the software, implementation services, training, and support described in Exhibit A.",
            },
          ],
        },
      ],
      term: [
        {
          label: "When it takes effect and how long it runs",
          answer:
            "The agreement becomes effective on execution and runs through the initial implementation and support term described in the contract.",
          citations: [
            {
              pageNumber: 4,
              snippet: "This Agreement shall commence on the Effective Date and continue for the term set forth herein.",
            },
          ],
        },
      ],
      economics: [
        {
          label: "How pricing works",
          answer:
            "Pricing is split across software fees, implementation services, and recurring support charges detailed in the exhibits.",
          citations: [
            {
              pageNumber: 18,
              snippet: "The fees for software, implementation services, and annual support are set forth in Exhibit B.",
            },
          ],
        },
      ],
      controls: [
        {
          label: "How termination or exit works",
          answer:
            "The contract includes standard breach-based termination mechanics and notice requirements.",
          citations: [
            {
              pageNumber: 10,
              snippet: "Either party may terminate this Agreement for material breach after notice and opportunity to cure.",
            },
          ],
        },
      ],
      quality: [
        {
          label: "Important caveats or ambiguities",
          answer:
            "Commercial detail is heavily exhibit-driven, so exact fees should be read with the pricing exhibit pages rather than the body alone.",
          citations: [
            {
              pageNumber: 18,
              snippet: "See Exhibit B for complete pricing detail.",
            },
          ],
        },
      ],
    },
    pageNotes: [
      {
        pageNumber: 1,
        pageRole: "operative_clause",
        summary:
          "Agreement cover page establishing parties and document identity.",
        keyTerms: ["master agreement", "Tyler Technologies", "Lake County"],
        relevanceTags: ["governing", "parties"],
      },
      {
        pageNumber: 18,
        pageRole: "pricing_or_rate_table",
        summary:
          "Exhibit pricing page with software, implementation, and support fee structure.",
        keyTerms: ["Exhibit B", "support fees", "implementation services"],
        relevanceTags: ["pricing"],
      },
    ],
    pages: [
      {
        pageNumber: 1,
        representation: "repair_markdown",
        sourcePath:
          "data/processed/contracts/23173_1_fully_executed_agreement_with_exhibits__870df94e/pages/001.repair.md",
        qualityFlags: [],
        excerpt:
          "Master services agreement between Lake County and Tyler Technologies, Inc. establishing the core operative contract.",
      },
      {
        pageNumber: 10,
        representation: "markdown",
        sourcePath:
          "data/processed/contracts/23173_1_fully_executed_agreement_with_exhibits__870df94e/pages/010.md",
        qualityFlags: [],
        excerpt:
          "Termination and cure clause with formal notice mechanics and post-breach remedies.",
      },
      {
        pageNumber: 18,
        representation: "repair_markdown",
        sourcePath:
          "data/processed/contracts/23173_1_fully_executed_agreement_with_exhibits__870df94e/pages/018.repair.md",
        qualityFlags: ["table_heavy"],
        excerpt:
          "Pricing exhibit page with implementation, license, and recurring support fees.",
      },
    ],
  },
  {
    id: "2024_03_07_contract_21022_modification_2_executed__e8f25a6a",
    title: "Contract 21022 modification no. 2",
    sourceFilename: "2024_03_07_contract_21022_modification_2_executed.pdf",
    overview:
      "Change document with a clear target artifact, concrete pricing and scope deltas, and enough clause anchors to route a later question-specific extraction pass.",
    procurement: {
      buyer: "Lake County, Illinois",
      seller: "Compass Minerals America, Inc.",
      subject: "Road salt supply and related pricing terms",
      category: "maintenance_operations",
      summary:
        "County purchase of operational materials with later change documents adjusting scope and commercial terms.",
    },
    classification: {
      procurementStage: "active_change",
      primaryDocumentRole: "delta",
      changeKind: "amendment",
      confidence: 0.94,
    },
    documentMapType: "change",
    changeNotes: {
      targetArtifact: {
        label: "Target artifact",
        answer:
          "This modification amends contract 21022 covering the County's road salt supply arrangement with Compass Minerals.",
        citations: [
          {
            pageNumber: 1,
            snippet: "Modification No. 2 to Contract 21022 between Lake County and Compass Minerals America, Inc.",
          },
        ],
      },
      change: {
        label: "What changed",
        answer:
          "The modification revises quantities, adjusts pricing terms, and updates related performance language tied to salt delivery and supply.",
        dimensions: ["scope", "pricing", "control"],
        citations: [
          {
            pageNumber: 2,
            snippet: "The contract quantities are revised as set forth below and the pricing schedule is amended accordingly.",
          },
        ],
      },
      resultingState: {
        label: "Resulting state",
        answer:
          "After the change, the amended quantity schedule and revised pricing terms govern future supply under contract 21022.",
        citations: [
          {
            pageNumber: 3,
            snippet: "All other terms remain in effect except as expressly amended herein.",
          },
        ],
      },
      keyClauses: [
        {
          label: "Target linkage",
          summary: "Opening paragraph identifies contract 21022 as the amended artifact.",
          citations: [
            {
              pageNumber: 1,
              snippet: "Modification No. 2 to Contract 21022",
            },
          ],
        },
        {
          label: "Pricing delta",
          summary: "Pricing schedule is revised in the modification body.",
          citations: [
            {
              pageNumber: 2,
              snippet: "The pricing schedule is amended as follows...",
            },
          ],
        },
      ],
    },
    pageNotes: [
      {
        pageNumber: 1,
        pageRole: "change_clause",
        summary: "Opening amendment page identifying the target contract and parties.",
        keyTerms: ["Modification No. 2", "Contract 21022", "Compass Minerals"],
        relevanceTags: ["change", "parties"],
      },
      {
        pageNumber: 2,
        pageRole: "pricing_or_rate_table",
        summary:
          "Core delta page revising quantities and pricing for future deliveries.",
        keyTerms: ["pricing schedule", "quantities", "delivery"],
        relevanceTags: ["change", "pricing", "scope"],
      },
    ],
    pages: [
      {
        pageNumber: 1,
        representation: "markdown",
        sourcePath:
          "data/processed/contracts/2024_03_07_contract_21022_modification_2_executed__e8f25a6a/pages/001.md",
        qualityFlags: [],
        excerpt:
          "Modification title page linking the delta to the prior contract and parties.",
      },
      {
        pageNumber: 2,
        representation: "repair_markdown",
        sourcePath:
          "data/processed/contracts/2024_03_07_contract_21022_modification_2_executed__e8f25a6a/pages/002.repair.md",
        qualityFlags: ["table_heavy"],
        excerpt:
          "Operative modification language revising the schedule, pricing, and delivery obligations.",
      },
      {
        pageNumber: 3,
        representation: "ocr_text",
        sourcePath:
          "data/processed/contracts/2024_03_07_contract_21022_modification_2_executed__e8f25a6a/pages/003.ocr.txt",
        qualityFlags: ["ocr_source"],
        excerpt:
          "Remainder clause confirming unchanged terms other than the explicit modifications.",
      },
    ],
  },
  {
    id: "24253_award_letter__5aa7a6c1",
    title: "Award letter for behavioral health services",
    sourceFilename: "24253_award_letter.pdf",
    overview:
      "Context document useful for procurement history and vendor selection, but not the operative governing contract.",
    procurement: {
      buyer: "Lake County, Illinois",
      seller: "The Josselyn Center",
      subject: "Behavioral health service award notice",
      category: "behavioral_health",
      summary:
        "Award-stage procurement context identifying the selected vendor before execution of the later governing agreement.",
    },
    classification: {
      procurementStage: "award",
      primaryDocumentRole: "context",
      confidence: 0.91,
    },
    documentMapType: "context",
    pageNotes: [
      {
        pageNumber: 1,
        pageRole: "supporting_context",
        summary:
          "Award notice identifying selected vendor and procurement outcome.",
        keyTerms: ["award letter", "selected vendor", "behavioral health"],
        relevanceTags: ["procurement_history"],
      },
    ],
    pages: [
      {
        pageNumber: 1,
        representation: "markdown",
        sourcePath:
          "data/processed/contracts/24253_award_letter__5aa7a6c1/pages/001.md",
        qualityFlags: [],
        excerpt:
          "Award letter naming the selected provider and providing pre-contract procurement context.",
      },
    ],
  },
  {
    id: "18_0386_fairfield_at_monaville_phase_ii__f1062b46",
    title: "Fairfield at Monaville Phase II support packet",
    sourceFilename: "18_0386_Fairfield_at_Monaville_Phase_II.pdf",
    overview:
      "Large supporting packet where page notes are critical because the document is too dense and diffuse to read whole every time.",
    procurement: {
      buyer: "Lake County Stormwater Management Commission",
      seller: "Fairfield at Monaville development entities",
      subject: "Engineering and stormwater support packet",
      category: "engineering_construction",
      summary:
        "Dense supporting packet with maps, exhibits, and contextual material rather than a single operative agreement.",
    },
    classification: {
      procurementStage: "compliance",
      primaryDocumentRole: "context",
      confidence: 0.83,
    },
    documentMapType: "context",
    pageNotes: [
      {
        pageNumber: 4,
        pageRole: "supporting_context",
        summary: "Project narrative and development context.",
        keyTerms: ["Phase II", "stormwater", "narrative"],
        relevanceTags: ["procurement_history"],
      },
      {
        pageNumber: 18,
        pageRole: "pricing_or_rate_table",
        summary: "Cost schedule and engineering estimate table.",
        keyTerms: ["cost estimate", "construction", "schedule"],
        relevanceTags: ["pricing"],
      },
      {
        pageNumber: 42,
        pageRole: "operative_clause",
        summary: "Conditions and obligations page with compliance-style requirements.",
        keyTerms: ["conditions", "obligations", "compliance"],
        relevanceTags: ["compliance"],
      },
    ],
    pages: [
      {
        pageNumber: 4,
        representation: "repair_markdown",
        sourcePath:
          "data/processed/contracts/18_0386_fairfield_at_monaville_phase_ii__f1062b46/pages/004.repair.md",
        qualityFlags: [],
        excerpt:
          "Narrative project description and overall development context.",
      },
      {
        pageNumber: 18,
        representation: "repair_markdown",
        sourcePath:
          "data/processed/contracts/18_0386_fairfield_at_monaville_phase_ii__f1062b46/pages/018.repair.md",
        qualityFlags: ["table_heavy"],
        excerpt:
          "Cost estimate page summarizing engineering and construction items.",
      },
      {
        pageNumber: 42,
        representation: "ocr_text",
        sourcePath:
          "data/processed/contracts/18_0386_fairfield_at_monaville_phase_ii__f1062b46/pages/042.ocr.txt",
        qualityFlags: ["ocr_source", "dense_scan"],
        excerpt:
          "Conditions page with dense compliance language requiring page-note guidance before deeper review.",
      },
    ],
  },
  {
    id: "behavioral_services_center_professional_agreement__320766a0",
    title: "Behavioral services center professional agreement",
    sourceFilename: "behavioral_services_center_professional_agreement_fully_executed.pdf",
    overview:
      "Executed professional services agreement for behavioral health delivery, with a usable governing note layer and a small number of pages worth opening directly.",
    procurement: {
      buyer: "Lake County, Illinois",
      seller: "The Josselyn Center",
      subject: "Behavioral health professional services",
      category: "behavioral_health",
      summary:
        "County behavioral health services arrangement with a clear operative agreement and supporting pricing and term language.",
    },
    classification: {
      procurementStage: "contracting",
      primaryDocumentRole: "operative",
      confidence: 0.93,
    },
    documentMapType: "governing",
    governingNotes: {
      identity: [
        {
          label: "What this document is",
          answer:
            "A fully executed professional services agreement governing behavioral health services for the County.",
          citations: [
            {
              pageNumber: 1,
              snippet:
                "This Professional Services Agreement is entered into by Lake County and The Josselyn Center.",
            },
          ],
        },
      ],
      parties: [
        {
          label: "Who the main parties are",
          answer:
            "Lake County is the public contracting party and The Josselyn Center is the service provider.",
          citations: [
            {
              pageNumber: 1,
              snippet: "Lake County, Illinois ... and The Josselyn Center",
            },
          ],
        },
      ],
      subject: [
        {
          label: "What is being bought or governed",
          answer:
            "Behavioral health professional services and related service-delivery obligations.",
          citations: [
            {
              pageNumber: 2,
              snippet: "Contractor shall provide behavioral health services as described herein.",
            },
          ],
        },
      ],
      term: [
        {
          label: "When it takes effect and how long it runs",
          answer:
            "The agreement runs for the stated service term after execution, subject to renewal or extension provisions in the contract.",
          citations: [
            {
              pageNumber: 3,
              snippet:
                "The term of this Agreement shall begin on the Effective Date and continue for the period stated below.",
            },
          ],
        },
      ],
      economics: [
        {
          label: "How pricing works",
          answer:
            "Compensation is governed by the contract fee schedule and invoicing provisions rather than a fixed one-line lump sum in the body.",
          citations: [
            {
              pageNumber: 5,
              snippet:
                "Compensation shall be paid in accordance with the fee schedule and invoice process set forth herein.",
            },
          ],
        },
      ],
      controls: [
        {
          label: "How termination or exit works",
          answer:
            "The agreement includes termination and notice mechanics tied to breach and contract administration.",
          citations: [
            {
              pageNumber: 7,
              snippet:
                "Either party may terminate this Agreement upon notice as provided in this section.",
            },
          ],
        },
      ],
      quality: [
        {
          label: "Important caveats or ambiguities",
          answer:
            "Exact commercial detail is spread across the compensation section and supporting schedules, so those pages should be read together.",
          citations: [
            {
              pageNumber: 5,
              snippet: "Compensation shall be paid in accordance with the fee schedule...",
            },
          ],
        },
      ],
    },
    pageNotes: [
      {
        pageNumber: 1,
        pageRole: "operative_clause",
        summary: "Agreement identity page establishing parties and contract type.",
        keyTerms: ["professional services agreement", "behavioral health"],
        relevanceTags: ["governing", "parties"],
      },
      {
        pageNumber: 5,
        pageRole: "pricing_or_rate_table",
        summary: "Compensation and invoice language worth checking for exact payment terms.",
        keyTerms: ["compensation", "invoice", "fee schedule"],
        relevanceTags: ["pricing"],
      },
    ],
    pages: [
      {
        pageNumber: 1,
        representation: "repair_markdown",
        sourcePath:
          "data/processed/contracts/behavioral_services_center_professional_agreement__320766a0/pages/001.repair.md",
        qualityFlags: [],
        excerpt:
          "Executed professional services agreement between Lake County and The Josselyn Center.",
      },
      {
        pageNumber: 5,
        representation: "markdown",
        sourcePath:
          "data/processed/contracts/behavioral_services_center_professional_agreement__320766a0/pages/005.md",
        qualityFlags: [],
        excerpt:
          "Compensation section and invoice mechanics for behavioral health services.",
      },
    ],
  },
  {
    id: "2025_01_15_contract_23173_4_renewal_letter_25_26__d8a4cc04",
    title: "Contract 23173 renewal letter",
    sourceFilename: "2025_01_15_contract_23173_4_renewal_letter_25_26.pdf",
    overview:
      "Simple renewal letter extending the current software relationship without the broader change complexity of a full amendment packet.",
    procurement: {
      buyer: "Lake County, Illinois",
      seller: "Tyler Technologies, Inc.",
      subject: "Software support renewal",
      category: "software_it",
      summary:
        "Later-stage change document extending an existing software support relationship into the next contract period.",
    },
    classification: {
      procurementStage: "active_change",
      primaryDocumentRole: "delta",
      changeKind: "renewal",
      confidence: 0.92,
    },
    documentMapType: "change",
    changeNotes: {
      targetArtifact: {
        label: "Target artifact",
        answer:
          "This renewal letter continues the existing Tyler software agreement for the next service period.",
        citations: [
          {
            pageNumber: 1,
            snippet: "This letter renews the current agreement for the 2025-2026 contract year.",
          },
        ],
      },
      change: {
        label: "What changed",
        answer:
          "The operative change is a renewal of the existing support term into the next contract period.",
        dimensions: ["term"],
        citations: [
          {
            pageNumber: 1,
            snippet: "The contract is hereby renewed for the upcoming term.",
          },
        ],
      },
      resultingState: {
        label: "Resulting state",
        answer:
          "The Tyler support relationship remains in force for the renewed term referenced in the letter.",
        citations: [
          {
            pageNumber: 1,
            snippet: "Upon acceptance, the renewed term shall remain in effect through the stated period.",
          },
        ],
      },
      keyClauses: [
        {
          label: "Renewal clause",
          summary: "The letter expressly renews the current agreement for the next term.",
          citations: [
            {
              pageNumber: 1,
              snippet: "The contract is hereby renewed for the upcoming term.",
            },
          ],
        },
      ],
    },
    pageNotes: [
      {
        pageNumber: 1,
        pageRole: "change_clause",
        summary: "Renewal letter with a simple term-extension style change.",
        keyTerms: ["renewal", "contract year", "Tyler"],
        relevanceTags: ["change", "term"],
      },
    ],
    pages: [
      {
        pageNumber: 1,
        representation: "markdown",
        sourcePath:
          "data/processed/contracts/2025_01_15_contract_23173_4_renewal_letter_25_26__d8a4cc04/pages/001.md",
        qualityFlags: [],
        excerpt:
          "Short renewal letter extending the Tyler agreement through the next contract period.",
      },
    ],
  },
  {
    id: "rfp_software_evaluation_summary__9c8a4471",
    title: "Software evaluation summary",
    sourceFilename: "software_evaluation_summary.pdf",
    overview:
      "Procurement-stage evaluation summary useful for vendor selection history and sourcing context, but not itself an operative contract.",
    procurement: {
      buyer: "Lake County, Illinois",
      seller: "Multiple responding vendors",
      subject: "Software procurement evaluation",
      category: "software_it",
      summary:
        "Pre-award evaluation material comparing vendors and documenting the County's procurement decision path.",
    },
    classification: {
      procurementStage: "sourcing",
      primaryDocumentRole: "context",
      confidence: 0.88,
    },
    documentMapType: "context",
    pageNotes: [
      {
        pageNumber: 3,
        pageRole: "supporting_context",
        summary: "Evaluation narrative explaining vendor scoring and recommendation logic.",
        keyTerms: ["evaluation", "recommendation", "vendor scoring"],
        relevanceTags: ["procurement_history"],
      },
      {
        pageNumber: 7,
        pageRole: "pricing_or_rate_table",
        summary: "Comparative scoring and cost table across vendors.",
        keyTerms: ["cost", "score", "vendor comparison"],
        relevanceTags: ["pricing", "procurement_history"],
      },
    ],
    pages: [
      {
        pageNumber: 3,
        representation: "repair_markdown",
        sourcePath:
          "data/processed/contracts/rfp_software_evaluation_summary__9c8a4471/pages/003.repair.md",
        qualityFlags: [],
        excerpt:
          "Narrative evaluation of responding vendors and procurement recommendation.",
      },
      {
        pageNumber: 7,
        representation: "repair_markdown",
        sourcePath:
          "data/processed/contracts/rfp_software_evaluation_summary__9c8a4471/pages/007.repair.md",
        qualityFlags: ["table_heavy"],
        excerpt:
          "Comparison table of cost, score, and selection criteria across vendors.",
      },
    ],
  },
];
