import { createBrowserRouter } from "react-router-dom";
import DraftGallery from "./pages/DraftGallery";
import ConsoleV2Geek from "./drafts/console/v2_geek_glow/ConsoleV2Geek";
import ConsoleV2OptionBBackup from "./drafts/console/v2_option_b_backup/ConsoleV2OptionBBackup";
import ConsoleV3CalmCockpit from "./drafts/console/v3_calm_cockpit/ConsoleV3CalmCockpit";
import ConsoleV4EntryCockpit from "./drafts/console/v4_entry_cockpit/ConsoleV4EntryCockpit";
import ConsoleV5GuidedCockpit from "./drafts/console/v5_guided_cockpit/ConsoleV5GuidedCockpit";
import LandingV1Feishu from "./drafts/landing/v1_feishu_clean/LandingV1Feishu";
import LandingV2Geek from "./drafts/landing/v2_geek_glow/LandingV2Geek";
import LandingV3Hybrid from "./drafts/landing/v3_hybrid/LandingV3Hybrid";
import LandingV4DayNight from "./drafts/landing/v4_day_night/LandingV4DayNight";
import LandingV5SequenceStory from "./drafts/landing/v5_sequence_story/LandingV5SequenceStory";
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
    path: "/drafts/landing/v5",
    element: <LandingV5SequenceStory />,
  },
  {
    path: "/drafts/landing/v5/*",
    element: <LandingV5SequenceStory />,
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
    path: "/drafts/console/v3",
    element: <ConsoleV3CalmCockpit />,
  },
  {
    path: "/drafts/console/v4",
    element: <ConsoleV4EntryCockpit />,
  },
  {
    path: "/drafts/console/v5",
    element: <ConsoleV5GuidedCockpit />,
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
