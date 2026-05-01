import { Braces, Image, Info, Search, Wrench } from "lucide-react";
import {
  eventLabel,
  hostedWebSearchDomainSummary,
  hostedWebSearchQuery,
  hostedWebSearchResultCount,
  imageGenerationDataUrl,
  isHostedWebSearchEvent,
  isImageGenerationEvent,
  toolCallArgumentSummary,
} from "@/screens/AssistantScreen/AssistantScreen.helpers";
import type { AssistantMessage } from "@/screens/AssistantScreen/AssistantScreen.types";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import styles from "./AssistantEventRow.module.css";

type AssistantEventRowProps = {
  message: AssistantMessage;
  onOpenDebug: (messageId: string) => void;
  onOpenDetail: (messageId: string) => void;
  onOpenImage: (messageId: string) => void;
};

function eventIcon(message: AssistantMessage) {
  if (isHostedWebSearchEvent(message)) {
    return <Search size={15} aria-hidden="true" />;
  }
  if (isImageGenerationEvent(message)) {
    return <Image size={15} aria-hidden="true" />;
  }
  if (message.kind === "tool_call") {
    return <Wrench size={15} aria-hidden="true" />;
  }
  return <Info size={15} aria-hidden="true" />;
}

function eventTitle(message: AssistantMessage): string {
  if (isHostedWebSearchEvent(message)) {
    return hostedWebSearchQuery(message);
  }
  if (message.kind === "tool_call") {
    return message.rawItem?.record.name ?? message.title;
  }
  return message.title || eventLabel(message);
}

function eventMeta(message: AssistantMessage): string {
  if (isHostedWebSearchEvent(message)) {
    const resultCount = hostedWebSearchResultCount(message);
    const domains = hostedWebSearchDomainSummary(message);
    return [
      resultCount > 0 ? `${resultCount} results` : "Search completed",
      domains,
    ]
      .filter(Boolean)
      .join(" · ");
  }
  if (message.kind === "tool_call") {
    return toolCallArgumentSummary(message);
  }
  return message.content;
}

export function AssistantEventRow({
  message,
  onOpenDebug,
  onOpenDetail,
  onOpenImage,
}: AssistantEventRowProps) {
  const imageUrl = isImageGenerationEvent(message)
    ? imageGenerationDataUrl(message)
    : null;

  return (
    <article className={styles.root}>
      <div className={styles.icon}>{eventIcon(message)}</div>
      <div className={styles.copy}>
        <span className={styles.label}>{eventLabel(message)}</span>
        <p className={styles.title}>{eventTitle(message)}</p>
        {eventMeta(message) ? <p className={styles.meta}>{eventMeta(message)}</p> : null}
      </div>
      <div className={styles.actions}>
        {imageUrl ? (
          <IconButton
            aria-label="Open generated image"
            onClick={() => onOpenImage(message.id)}
            tooltip="Open image"
          >
            <Image size={14} aria-hidden="true" />
          </IconButton>
        ) : null}
        <IconButton
          aria-label={`Open ${eventLabel(message)} details`}
          onClick={() => onOpenDetail(message.id)}
          tooltip="Details"
        >
          <Info size={14} aria-hidden="true" />
        </IconButton>
        <IconButton
          aria-label={`Open ${eventLabel(message)} debug JSON`}
          onClick={() => onOpenDebug(message.id)}
          tooltip="Debug JSON"
        >
          <Braces size={14} aria-hidden="true" />
        </IconButton>
      </div>
    </article>
  );
}

