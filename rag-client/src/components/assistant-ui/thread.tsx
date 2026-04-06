import { FinancialLoadingIcon } from "@/components/FinancialLoadingIcon";
import { PersonaSelector } from "@/components/PersonaSelector";
import { MarkdownText } from "@/components/assistant-ui/markdown-text";
import { ToolFallback } from "@/components/assistant-ui/tool-fallback";
import { TooltipIconButton } from "@/components/assistant-ui/tooltip-icon-button";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  ActionBarPrimitive,
  AuiIf,
  BranchPickerPrimitive,
  ComposerPrimitive,
  ErrorPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useAuiState,
} from "@assistant-ui/react";
import {
  ArrowDownIcon,
  ArrowUpIcon,
  CheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CopyIcon,
  PencilIcon,
  SquareIcon,
} from "lucide-react";
import { type FC, useEffect, useState } from "react";

export const Thread: FC = () => {
  const isEmpty = useAuiState((s) => s.thread.isEmpty);

  return (
    <ThreadPrimitive.Root
      className="aui-root aui-thread-root @container flex h-full flex-col bg-background"
      style={{
        ["--thread-max-width" as string]: "48rem",
        ["--composer-radius" as string]: "20px",
        ["--composer-padding" as string]: "12px",
      }}
    >
      <ThreadPrimitive.Viewport
        turnAnchor="top"
        className="aui-thread-viewport relative flex flex-1 flex-col overflow-x-auto overflow-y-scroll scroll-smooth px-4 pt-6 sm:px-6"
      >
        {isEmpty && <ThreadWelcome />}

        <ThreadPrimitive.Messages>
          {() => <ThreadMessage />}
        </ThreadPrimitive.Messages>

        <ThreadPrimitive.ViewportFooter
          className={cn(
            "aui-thread-viewport-footer sticky bottom-0 mx-auto mt-auto flex w-full max-w-(--thread-max-width) flex-col gap-3 overflow-visible rounded-t-(--composer-radius) bg-background pb-4 sm:pb-6",
            isEmpty && "hidden",
          )}
        >
          <ThreadScrollToBottom />
          <Composer />
        </ThreadPrimitive.ViewportFooter>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
};

const ThreadMessage: FC = () => {
  const role = useAuiState((s) => s.message.role);
  const isEditing = useAuiState((s) => s.message.composer.isEditing);
  if (isEditing) return <EditComposer />;
  if (role === "user") return <UserMessage />;
  return <AssistantMessage />;
};

const ThreadScrollToBottom: FC = () => {
  return (
    <ThreadPrimitive.ScrollToBottom
      className="aui-thread-scroll-to-bottom absolute -top-12 z-10 self-center rounded-full border border-border/60 bg-background/80 p-3 shadow-sm backdrop-blur-sm transition-all hover:bg-muted hover:shadow-md disabled:pointer-events-none disabled:hidden"
    >
      <ArrowDownIcon className="size-4" />
    </ThreadPrimitive.ScrollToBottom>
  );
};

const ThreadWelcome: FC = () => {
  return (
    <div className="aui-thread-welcome-root mx-auto flex w-full max-w-[48rem] flex-1 flex-col items-center justify-center px-4">
      <h1 className="fade-in slide-in-from-bottom-2 animate-in fill-mode-both mb-[0.58rem] text-center text-[2.16rem] font-bold tracking-tight text-foreground duration-300 sm:text-[2.59rem]">
        Hi there, I'm Ally.
      </h1>
      <p className="fade-in slide-in-from-bottom-2 animate-in fill-mode-both mb-[2.3rem] text-center text-[1.29rem] text-muted-foreground duration-500 delay-100 sm:text-[1.44rem]">
        Helping you get from Allan<span className="italic text-foreground">Gray</span>{" "}
        to Allan<span className="italic text-terracotta">Clear</span>
      </p>

      <ComposerPrimitive.Root className="aui-composer-root relative flex w-full flex-col">
        <div
          data-slot="composer-shell"
          className="flex w-full flex-col gap-3 rounded-[14px] border border-border bg-white p-[1.15rem] shadow-sm transition-all duration-150 focus-within:border-ring/50 focus-within:shadow-md focus-within:ring-2 focus-within:ring-ring/15"
        >
          <ComposerPrimitive.Input
            placeholder="Ask about investments, funds, or financial planning..."
            className="aui-composer-input max-h-[8.05rem] min-h-[3.45rem] w-full resize-none bg-transparent px-[0.58rem] py-[0.29rem] text-[1.15rem] leading-relaxed outline-none placeholder:text-muted-foreground/40 placeholder:font-normal"
            rows={1}
            autoFocus
            aria-label="Message input"
          />
          <ComposerAction />
        </div>
      </ComposerPrimitive.Root>

      <div className="mt-[1.44rem] w-full">
        <PersonaSelector />
      </div>
    </div>
  );
};

/* ── Loading / thinking indicator (rendered inside assistant message) ── */
const LOADING_VERBS = [
  "Compounding",
  "Diversifying",
  "Rebalancing",
  "Forecasting",
  "Calibrating",
  "Distilling",
  "Prospecting",
  "Synthesizing",
  "Crystallizing",
  "Appraising",
  "Auditing",
  "Quantifying",
  "Benchmarking",
  "Allocating",
  "Curating",
];

const AssistantLoadingText: FC = () => {
  const [phraseIndex, setPhraseIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setPhraseIndex((i) => (i + 1) % LOADING_VERBS.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <span className="inline-flex items-center gap-1.5 text-accent">
      <FinancialLoadingIcon className="text-accent" />
      <span
        key={phraseIndex}
        className="loading-text-pulse inline-block text-[16px] font-medium"
      >
        {LOADING_VERBS[phraseIndex]}...
      </span>
    </span>
  );
};

const AssistantMessageContent: FC = () => {
  const content = useAuiState((s) => s.message.content);
  const isRunning = useAuiState(
    (s) => s.message.status.type === "running",
  );

  const hasText = content.some(
    (part) => part.type === "text" && part.text.length > 0,
  );

  if (isRunning && !hasText) {
    return <AssistantLoadingText />;
  }

  return (
    <MessagePrimitive.Parts>
      {({ part }) => {
        if (part.type === "text") return <MarkdownText />;
        if (part.type === "tool-call")
          return part.toolUI ?? <ToolFallback {...part} />;
        return null;
      }}
    </MessagePrimitive.Parts>
  );
};

const Composer: FC = () => {
  return (
    <ComposerPrimitive.Root className="aui-composer-root relative flex w-full flex-col">
      <div
        data-slot="composer-shell"
        className="flex w-full flex-col gap-2 rounded-(--composer-radius) border border-border/60 bg-background p-(--composer-padding) shadow-sm transition-all duration-150 focus-within:border-ring/50 focus-within:shadow-md focus-within:ring-2 focus-within:ring-ring/15"
      >
        <ComposerPrimitive.Input
          placeholder="Ask about investments, funds, or financial planning..."
          className="aui-composer-input max-h-32 min-h-20 w-full resize-none bg-transparent px-2 py-1 text-[15px] leading-relaxed outline-none placeholder:text-muted-foreground/60"
          rows={1}
          autoFocus
          aria-label="Message input"
        />
        <ComposerAction />
      </div>
    </ComposerPrimitive.Root>
  );
};

const ComposerAction: FC = () => {
  return (
    <div className="aui-composer-action-wrapper relative flex items-center justify-end">
      <AuiIf condition={(s) => !s.thread.isRunning}>
        <ComposerPrimitive.Send
          render={
            <TooltipIconButton
              tooltip="Send message"
              side="bottom"
              type="button"
              variant="default"
              size="icon"
              className="aui-composer-send size-8 rounded-full transition-transform hover:scale-105 active:scale-95"
              aria-label="Send message"
            />
          }
        >
        </ComposerPrimitive.Send>
      </AuiIf>
      <AuiIf condition={(s) => s.thread.isRunning}>
        <ComposerPrimitive.Cancel
          render={
            <Button
              type="button"
              variant="default"
              size="icon"
              className="aui-composer-cancel size-8 rounded-full transition-transform hover:scale-105 active:scale-95"
              aria-label="Stop generating"
            />
          }
        >
          <SquareIcon className="aui-composer-cancel-icon size-3 fill-current" />
        </ComposerPrimitive.Cancel>
      </AuiIf>
    </div>
  );
};

const MessageError: FC = () => {
  return (
    <MessagePrimitive.Error>
      <ErrorPrimitive.Root className="aui-message-error-root mt-3 rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-destructive text-sm">
        <ErrorPrimitive.Message className="aui-message-error-message line-clamp-2" />
      </ErrorPrimitive.Root>
    </MessagePrimitive.Error>
  );
};

const AssistantMessage: FC = () => {
  return (
    <MessagePrimitive.Root
      className="group/msg aui-assistant-message-root fade-in slide-in-from-bottom-1 relative mx-auto flex w-full max-w-(--thread-max-width) animate-in items-start gap-2 py-4 duration-200"
      data-role="assistant"
    >
      <div className="aui-assistant-message-content min-w-0 flex-1 wrap-break-word px-2 text-[17px] leading-[1.65] text-foreground">
        <AssistantMessageContent />
        <MessageError />
      </div>

      <div className="mt-1 shrink-0 opacity-0 transition-opacity duration-150 group-hover/msg:opacity-100">
        <AssistantActionBar />
      </div>
    </MessagePrimitive.Root>
  );
};

const AssistantActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      className="aui-assistant-action-bar-root flex text-muted-foreground"
    >
      <ActionBarPrimitive.Copy
        className="inline-flex size-7 items-center justify-center rounded-md transition-colors hover:bg-muted hover:text-foreground [&>svg]:size-3.5"
      >
        <AuiIf condition={(s) => s.message.isCopied}>
          <CheckIcon />
        </AuiIf>
        <AuiIf condition={(s) => !s.message.isCopied}>
          <CopyIcon />
        </AuiIf>
      </ActionBarPrimitive.Copy>
    </ActionBarPrimitive.Root>
  );
};

const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root
      className="aui-user-message-root fade-in slide-in-from-bottom-1 mx-auto grid w-full max-w-(--thread-max-width) animate-in auto-rows-auto grid-cols-[minmax(72px,1fr)_auto] content-start gap-y-2 px-2 py-4 duration-200 [&:where(>*)]:col-start-2"
      data-role="user"
    >
      <div className="aui-user-message-content-wrapper relative col-start-2 min-w-0">
        <div className="aui-user-message-content wrap-break-word peer rounded-2xl bg-muted px-4 py-3 text-[17px] leading-[1.65] text-foreground empty:hidden">
          <MessagePrimitive.Parts />
        </div>
        <div className="aui-user-action-bar-wrapper absolute top-1/2 left-0 -translate-x-full -translate-y-1/2 pr-2 peer-empty:hidden">
          <UserActionBar />
        </div>
      </div>

      <BranchPicker className="aui-user-branch-picker col-span-full col-start-1 row-start-3 -mr-1 justify-end" />
    </MessagePrimitive.Root>
  );
};

const UserActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      className="aui-user-action-bar-root flex flex-col items-end"
    >
      <ActionBarPrimitive.Edit
        render={
          <TooltipIconButton
            tooltip="Edit"
            className="aui-user-action-edit p-3 transition-colors hover:text-foreground"
          />
        }
      >
        <PencilIcon />
      </ActionBarPrimitive.Edit>
    </ActionBarPrimitive.Root>
  );
};

const EditComposer: FC = () => {
  return (
    <MessagePrimitive.Root className="aui-edit-composer-wrapper mx-auto flex w-full max-w-(--thread-max-width) flex-col px-2 py-3">
      <ComposerPrimitive.Root className="aui-edit-composer-root ml-auto flex w-full max-w-[85%] flex-col rounded-2xl bg-muted">
        <ComposerPrimitive.Input
          className="aui-edit-composer-input min-h-14 w-full resize-none bg-transparent p-4 text-[15px] text-foreground outline-none"
          autoFocus
        />
        <div className="aui-edit-composer-footer mx-3 mb-3 flex items-center gap-2 self-end">
          <ComposerPrimitive.Cancel render={<Button variant="ghost" size="sm" />}>
            Cancel
          </ComposerPrimitive.Cancel>
          <ComposerPrimitive.Send render={<Button size="sm" />}>
            Update
          </ComposerPrimitive.Send>
        </div>
      </ComposerPrimitive.Root>
    </MessagePrimitive.Root>
  );
};

const BranchPicker: FC<BranchPickerPrimitive.Root.Props> = ({
  className,
  ...rest
}) => {
  return (
    <BranchPickerPrimitive.Root
      hideWhenSingleBranch
      className={cn(
        "aui-branch-picker-root mr-2 -ml-2 inline-flex items-center text-muted-foreground text-xs",
        className,
      )}
      {...rest}
    >
      <BranchPickerPrimitive.Previous
        render={<TooltipIconButton tooltip="Previous" />}
      >
        <ChevronLeftIcon />
      </BranchPickerPrimitive.Previous>
      <span className="aui-branch-picker-state font-medium">
        <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      </span>
      <BranchPickerPrimitive.Next
        render={<TooltipIconButton tooltip="Next" />}
      >
        <ChevronRightIcon />
      </BranchPickerPrimitive.Next>
    </BranchPickerPrimitive.Root>
  );
};
