"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useAuthStore } from "@/stores/auth-store";
import { projects as projectsApi, type Project } from "@/lib/api";
import {
  Zap,
  ArrowLeft,
  Send,
  Code2,
  DollarSign,
  FileText,
  Network,
  MessageSquare,
  Loader2,
  Terminal,
  Download,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

export default function WorkspacePage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.id as string;
  const { accessToken, isAuthenticated } = useAuthStore();

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [activePanelTab, setActivePanelTab] = useState("code");
  const [chatMessages, setChatMessages] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([
    {
      role: "assistant",
      content:
        "Welcome to InfraGen! Describe the infrastructure you need, and I'll generate Terraform code, architecture diagrams, and cost estimates for you.\n\nTry something like:\n• \"3-tier web app on AWS with React, Node.js, and PostgreSQL\"\n• \"Serverless API with Lambda, API Gateway, and DynamoDB\"\n• \"Kubernetes cluster with auto-scaling and monitoring\"",
    },
  ]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/");
      return;
    }
    loadProject();
  }, [isAuthenticated, projectId]);

  const loadProject = async () => {
    if (!accessToken) return;
    try {
      const data = await projectsApi.get(accessToken, projectId);
      setProject(data);
    } catch {
      router.push("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    setChatMessages((prev) => [...prev, { role: "user", content: message }]);

    // Placeholder AI response (will be replaced with real AI integration)
    setTimeout(() => {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "🔄 AI generation will be connected in Week 3-4. For now, the workspace layout is ready!\n\nThis is where you'll see:\n• Generated Terraform code in the Code panel\n• Architecture diagrams in the Diagram panel\n• Cost estimates in the Cost panel",
        },
      ]);
    }, 500);

    setMessage("");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      {/* Top bar */}
      <header className="h-12 border-b border-border/50 bg-card/50 backdrop-blur-sm flex items-center px-4 gap-3 shrink-0">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => router.push("/dashboard")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <Separator orientation="vertical" className="h-5" />
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-6 h-6 rounded bg-primary text-primary-foreground">
            <Zap className="w-3 h-3" />
          </div>
          <span className="text-sm font-medium truncate max-w-[200px]">{project?.name}</span>
        </div>
        <Badge variant="outline" className="text-[10px] h-5 font-mono ml-1">
          {project?.cloud_provider.toUpperCase()}
        </Badge>
        <Badge variant="outline" className="text-[10px] h-5 font-mono">
          {project?.iac_tool}
        </Badge>

        <div className="ml-auto flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger
              render={<Button variant="ghost" size="icon" className="h-8 w-8" disabled />}
            >
              <Download className="h-4 w-4" />
            </TooltipTrigger>
            <TooltipContent>Export as ZIP</TooltipContent>
          </Tooltip>
        </div>
      </header>

      {/* Main workspace: 3-pane layout */}
      <div className="flex-1 flex min-h-0">
        {/* Left: Chat panel */}
        <div className="w-[340px] border-r border-border/50 flex flex-col shrink-0">
          <div className="h-10 border-b border-border/50 flex items-center px-4">
            <MessageSquare className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Chat
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            {chatMessages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[90%] rounded-lg px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
          </div>

          {/* Input */}
          <form onSubmit={handleSendMessage} className="p-3 border-t border-border/50">
            <div className="flex gap-2">
              <Input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Describe your infrastructure..."
                className="text-sm bg-background/50"
              />
              <Button type="submit" size="icon" className="shrink-0" disabled={!message.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </form>
        </div>

        {/* Center: Diagram panel */}
        <div className="flex-1 flex flex-col min-w-0 border-r border-border/50">
          <div className="h-10 border-b border-border/50 flex items-center px-4">
            <Network className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Architecture Diagram
            </span>
          </div>

          <div className="flex-1 flex items-center justify-center bg-background/50">
            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center mx-auto mb-4">
                <Network className="h-8 w-8 text-muted-foreground/50" />
              </div>
              <p className="text-sm text-muted-foreground">
                Architecture diagram will appear here
              </p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                Describe your infrastructure in the chat to generate
              </p>
            </div>
          </div>
        </div>

        {/* Right: Code / Cost / Docs panel */}
        <div className="w-[400px] flex flex-col shrink-0">
          <div className="h-10 border-b border-border/50 flex items-center px-2">
            <Tabs value={activePanelTab} onValueChange={setActivePanelTab} className="w-full">
              <TabsList className="h-8 w-full bg-transparent p-0 gap-0">
                <TabsTrigger
                  value="code"
                  className="h-7 text-xs data-[state=active]:bg-muted rounded-sm px-3 gap-1.5"
                >
                  <Code2 className="h-3 w-3" />
                  Code
                </TabsTrigger>
                <TabsTrigger
                  value="cost"
                  className="h-7 text-xs data-[state=active]:bg-muted rounded-sm px-3 gap-1.5"
                >
                  <DollarSign className="h-3 w-3" />
                  Cost
                </TabsTrigger>
                <TabsTrigger
                  value="docs"
                  className="h-7 text-xs data-[state=active]:bg-muted rounded-sm px-3 gap-1.5"
                >
                  <FileText className="h-3 w-3" />
                  Docs
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          <div className="flex-1 flex items-center justify-center">
            {activePanelTab === "code" && (
              <div className="text-center px-6">
                <div className="w-12 h-12 rounded-xl bg-muted/50 flex items-center justify-center mx-auto mb-3">
                  <Terminal className="h-6 w-6 text-muted-foreground/50" />
                </div>
                <p className="text-sm text-muted-foreground">
                  Generated Terraform files will appear here
                </p>
                <p className="text-xs text-muted-foreground/70 mt-1">
                  With syntax highlighting and file tree
                </p>
              </div>
            )}
            {activePanelTab === "cost" && (
              <div className="text-center px-6">
                <div className="w-12 h-12 rounded-xl bg-muted/50 flex items-center justify-center mx-auto mb-3">
                  <DollarSign className="h-6 w-6 text-muted-foreground/50" />
                </div>
                <p className="text-sm text-muted-foreground">
                  Cost breakdown will appear here
                </p>
                <p className="text-xs text-muted-foreground/70 mt-1">
                  Per-service estimates with optimization hints
                </p>
              </div>
            )}
            {activePanelTab === "docs" && (
              <div className="text-center px-6">
                <div className="w-12 h-12 rounded-xl bg-muted/50 flex items-center justify-center mx-auto mb-3">
                  <FileText className="h-6 w-6 text-muted-foreground/50" />
                </div>
                <p className="text-sm text-muted-foreground">
                  Generated documentation will appear here
                </p>
                <p className="text-xs text-muted-foreground/70 mt-1">
                  ADRs, READMEs, and runbooks
                </p>
              </div>
            )}
          </div>

          {/* Validation bar */}
          <div className="h-9 border-t border-border/50 flex items-center px-4 gap-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-emerald-500" />
              0 errors
            </div>
            <div className="flex items-center gap-1">
              <AlertTriangle className="h-3 w-3 text-amber-500" />
              0 warnings
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
