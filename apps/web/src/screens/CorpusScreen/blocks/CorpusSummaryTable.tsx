import type { CorpusDocument } from "@/screens/CorpusScreen/CorpusScreen.types";
import { DefinitionGrid } from "@/ui/patterns/DefinitionGrid/DefinitionGrid";
import styles from "./CorpusSummaryTable.module.css";

type CorpusSummaryTableProps = {
  document: CorpusDocument;
};

export function CorpusSummaryTable({ document }: CorpusSummaryTableProps) {
  const rows = [
    { label: "Parties", value: document.summary.parties.join(" / ") },
    { label: "Subject", value: document.summary.subject },
    {
      label: "Procurement category",
      value: document.summary.procurementCategory,
    },
  ];

  return (
    <article className={styles.root}>
      <div className={styles.header}>
        <div>
          <p>Document summary</p>
          <h2>{document.title}</h2>
        </div>
      </div>

      <DefinitionGrid
        items={rows.map((row) => ({
          label: row.label,
          value: row.value,
        }))}
        variant="table"
      />
    </article>
  );
}
