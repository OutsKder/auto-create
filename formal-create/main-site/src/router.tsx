import { createBrowserRouter } from "react-router-dom";
import DraftGallery from "./pages/DraftGallery";
import ConsoleV2Geek from "./drafts/console/v2_geek_glow/ConsoleV2Geek";
import ConsoleV2OptionBBackup from "./drafts/console/v2_option_b_backup/ConsoleV2OptionBBackup";
import LandingV1Feishu from "./drafts/landing/v1_feishu_clean/LandingV1Feishu";
import LandingV2Geek from "./drafts/landing/v2_geek_glow/LandingV2Geek";
import LandingV3Hybrid from "./drafts/landing/v3_hybrid/LandingV3Hybrid";
import LandingV4DayNight from "./drafts/landing/v4_day_night/LandingV4DayNight";
import LoginV2Geek from "./drafts/login/v2_geek_glow/LoginV2Geek";
import OnboardingV2RoleCard from "./drafts/onboarding/v2_role_card/OnboardingV2RoleCard";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <DraftGallery />,
  },
  {
    path: "/drafts/landing/v1",
    element: <LandingV1Feishu />,
  },
  {
    path: "/drafts/landing/v2",
    element: <LandingV2Geek />,
  },
  {
    path: "/drafts/landing/v3",
    element: <LandingV3Hybrid />,
  },
  {
    path: "/drafts/landing/v4",
    element: <LandingV4DayNight />,
  },
  {
    path: "/drafts/landing/v4/*",
    element: <LandingV4DayNight />,
  },
  {
    path: "/drafts/console/v2",
    element: <ConsoleV2Geek />,
  },
  {
    path: "/drafts/console/v2-option-b",
    element: <ConsoleV2Geek />,
  },
  {
    path: "/drafts/console/v2-option-b-backup",
    element: <ConsoleV2OptionBBackup />,
  },
  {
    path: "/drafts/onboarding/v2",
    element: <OnboardingV2RoleCard />,
  },
  {
    path: "/drafts/login/v2",
    element: <LoginV2Geek />,
  },
  {
    path: "*",
    element: <DraftGallery />,
  },
]);
