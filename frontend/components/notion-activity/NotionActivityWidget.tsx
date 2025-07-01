"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RefreshCw, FileText, Search, Edit, CheckCircle, XCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatDistanceToNow } from "date-fns";

interface NotionActivity {
  timestamp: string;
  operation: string;
  details: Record<string, any>;
  success: boolean;
}

interface ActivitySummary {
  total_operations: number;
  operation_breakdown: Record<string, number>;
  pages_read: number;
  pages_created: number;
  last_activity: NotionActivity | null;
  recent_activities: NotionActivity[];
  tracked_since: string | null;
}

interface LiveStatus {
  is_active: boolean;
  last_activity: string | null;
  operations_today: number;
  pages_read_total: number;
  pages_created_total: number;
  tracking_since: string | null;
}

export function NotionActivityWidget() {
  const [summary, setSummary] = useState<ActivitySummary | null>(null);
  const [liveStatus, setLiveStatus] = useState<LiveStatus | null>(null);
  const [recentReads, setRecentReads] = useState<NotionActivity[]>([]);
  const [recentWrites, setRecentWrites] = useState<NotionActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchData = async () => {
    try {
      setError(null);
      
      // Fetch all data in parallel
      const [summaryRes, statusRes, readsRes, writesRes] = await Promise.all([
        fetch("/api/v1/notion-activity/summary"),
        fetch("/api/v1/notion-activity/live-status"),
        fetch("/api/v1/notion-activity/recent-reads?limit=5"),
        fetch("/api/v1/notion-activity/recent-writes?limit=5"),
      ]);

      if (!summaryRes.ok || !statusRes.ok || !readsRes.ok || !writesRes.ok) {
        throw new Error("Failed to fetch Notion activity data");
      }

      const summaryData = await summaryRes.json();
      const statusData = await statusRes.json();
      const readsData = await readsRes.json();
      const writesData = await writesRes.json();

      setSummary(summaryData.data);
      setLiveStatus(statusData.status);
      setRecentReads(readsData.reads);
      setRecentWrites(writesData.writes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const getOperationIcon = (operation: string) => {
    switch (operation) {
      case "read_page":
      case "get_page":
        return <FileText className="h-4 w-4" />;
      case "search_pages":
      case "query_database":
        return <Search className="h-4 w-4" />;
      case "create_page":
      case "update_page":
      case "append_to_page":
        return <Edit className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const getOperationColor = (operation: string) => {
    if (operation.includes("read") || operation.includes("get") || operation.includes("search")) {
      return "blue";
    }
    if (operation.includes("create") || operation.includes("update") || operation.includes("append")) {
      return "green";
    }
    return "gray";
  };

  const formatOperation = (operation: string) => {
    return operation
      .split("_")
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Notion Activity</CardTitle>
          <CardDescription>Loading activity data...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Notion Activity</CardTitle>
          <CardDescription>Error loading activity data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4">
            <p className="text-red-500 mb-4">{error}</p>
            <Button onClick={fetchData} variant="outline">
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Notion Activity</CardTitle>
            <CardDescription>
              Track agent interactions with your Notion workspace
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={autoRefresh ? "bg-primary text-primary-foreground" : ""}
            >
              {autoRefresh ? "Auto-refresh ON" : "Auto-refresh OFF"}
            </Button>
            <Button onClick={fetchData} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Live Status Bar */}
        {liveStatus && (
          <div className="mb-6 p-4 rounded-lg bg-muted">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {liveStatus.is_active ? (
                  <div className="h-3 w-3 bg-green-500 rounded-full animate-pulse" />
                ) : (
                  <div className="h-3 w-3 bg-gray-400 rounded-full" />
                )}
                <span className="font-medium">
                  {liveStatus.is_active ? "Active" : "Inactive"}
                </span>
              </div>
              {liveStatus.last_activity && (
                <span className="text-sm text-muted-foreground">
                  Last activity {formatDistanceToNow(new Date(liveStatus.last_activity), { addSuffix: true })}
                </span>
              )}
            </div>
            <div className="grid grid-cols-3 gap-4 mt-3">
              <div>
                <p className="text-sm text-muted-foreground">Today</p>
                <p className="text-2xl font-bold">{liveStatus.operations_today}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Pages Read</p>
                <p className="text-2xl font-bold">{liveStatus.pages_read_total}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Pages Created</p>
                <p className="text-2xl font-bold">{liveStatus.pages_created_total}</p>
              </div>
            </div>
          </div>
        )}

        {/* Activity Tabs */}
        <Tabs defaultValue="summary" className="space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="summary">Summary</TabsTrigger>
            <TabsTrigger value="reads">Recent Reads</TabsTrigger>
            <TabsTrigger value="writes">Recent Writes</TabsTrigger>
          </TabsList>

          <TabsContent value="summary" className="space-y-4">
            {summary && (
              <>
                {/* Operation Breakdown */}
                {Object.keys(summary.operation_breakdown).length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-3">Operations Breakdown</h4>
                    <div className="space-y-2">
                      {Object.entries(summary.operation_breakdown).map(([op, count]) => (
                        <div key={op} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {getOperationIcon(op)}
                            <span className="text-sm">{formatOperation(op)}</span>
                          </div>
                          <Badge variant="secondary">{count}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent Activities */}
                {summary.recent_activities.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-3">Recent Activities</h4>
                    <ScrollArea className="h-[200px]">
                      <div className="space-y-2">
                        {summary.recent_activities.map((activity, index) => (
                          <div
                            key={index}
                            className="flex items-start gap-3 p-2 rounded-md hover:bg-muted"
                          >
                            <div className={`mt-0.5 text-${getOperationColor(activity.operation)}-500`}>
                              {getOperationIcon(activity.operation)}
                            </div>
                            <div className="flex-1 space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-medium">
                                  {formatOperation(activity.operation)}
                                </span>
                                {activity.success ? (
                                  <CheckCircle className="h-3 w-3 text-green-500" />
                                ) : (
                                  <XCircle className="h-3 w-3 text-red-500" />
                                )}
                              </div>
                              <p className="text-xs text-muted-foreground">
                                {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                              </p>
                              {activity.details.page_id && (
                                <p className="text-xs text-muted-foreground font-mono">
                                  {activity.details.page_id}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>
                )}
              </>
            )}
          </TabsContent>

          <TabsContent value="reads" className="space-y-4">
            <ScrollArea className="h-[300px]">
              {recentReads.length > 0 ? (
                <div className="space-y-3">
                  {recentReads.map((read, index) => (
                    <div key={index} className="p-3 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-blue-500" />
                          <span className="font-medium text-sm">
                            {formatOperation(read.operation)}
                          </span>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(read.timestamp), { addSuffix: true })}
                        </span>
                      </div>
                      {read.details.page_url && (
                        <a
                          href={read.details.page_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-500 hover:underline block truncate"
                        >
                          {read.details.page_url}
                        </a>
                      )}
                      {read.details.query && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Search: "{read.details.query}"
                        </p>
                      )}
                      {read.details.results_count !== undefined && (
                        <p className="text-xs text-muted-foreground">
                          Found {read.details.results_count} results
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No recent reads found
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="writes" className="space-y-4">
            <ScrollArea className="h-[300px]">
              {recentWrites.length > 0 ? (
                <div className="space-y-3">
                  {recentWrites.map((write, index) => (
                    <div key={index} className="p-3 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Edit className="h-4 w-4 text-green-500" />
                          <span className="font-medium text-sm">
                            {formatOperation(write.operation)}
                          </span>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(write.timestamp), { addSuffix: true })}
                        </span>
                      </div>
                      {write.details.page_url && (
                        <a
                          href={write.details.page_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-500 hover:underline block truncate"
                        >
                          {write.details.page_url}
                        </a>
                      )}
                      {write.details.properties && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Properties: {Object.keys(write.details.properties).join(", ")}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No recent writes found
                </div>
              )}
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}