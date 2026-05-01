import { createBrowserRouter, Navigate } from "react-router-dom";
import { AuthGate } from "@/app/auth/AuthGate";
import { AppShell } from "@/app/AppShell";
import { CorpusRoute } from "@/app/routes/CorpusRoute";
import { AssistantScreen } from "@/screens/AssistantScreen/AssistantScreen";

export const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <AuthGate>
        <AppShell />
      </AuthGate>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/corpus" replace />,
      },
      {
        path: "corpus",
        element: <CorpusRoute />,
      },
      {
        path: "assistant",
        element: <AssistantScreen />,
      },
    ],
  },
]);
