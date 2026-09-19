import { LuTrophy } from "react-icons/lu";
import {
  HiOutlineChatBubbleLeftRight,
  HiOutlineCog6Tooth,
  HiOutlinePlayCircle,
  HiOutlinePresentationChartLine,
  HiOutlineShieldCheck,
  HiOutlineUsers,
} from "react-icons/hi2";
import { RiSpeakLine, RiUserCommunityFill } from "react-icons/ri";
import { GiSpellBook } from "react-icons/gi";

/**
 * Copied verbatim from the retiring client, because they are content rather
 * than code: the RCGP clinical capability wording and the product's own
 * navigation names both appear on the landing page and must not be reworded
 * by a port.
 *
 * NAV_LINKS keeps its `icon` fields: the hero's screenshot showcase reads
 * them to label each tab.
 */

export const CAPABILITIES = [
  {
    id: 1,
    capability: "Infants, children and young people (under the age of 19)",
    value: 1,
  },
  {
    id: 2,
    capability:
      "Mental health (including addiction, alcohol and substance misuse)",
    value: 2,
  },
  {
    id: 3,
    capability:
      "People with long term conditions including cancer, multi-morbidity and disability",
    value: 6,
  },
  {
    id: 4,
    capability: "Older adults including frailty and/or people at end of life",
    value: 4,
  },
  {
    id: 5,
    capability:
      "Gender, reproductive and sexual health (including women's, men's, LGBTQ, gynaecology and breast)",
    value: 3,
  },
  { id: 6, capability: "Urgent and unscheduled care", value: 3 },
  {
    id: 7,
    capability:
      "People with health disadvantage and vulnerabilities (including veterans, mental capacity difficulties, safeguarding and those with communication difficulties/disability)",
    value: 3,
  },
  {
    id: 8,
    capability:
      "Population Health and health promotion (including people with non-acute and/or non-chronic health problems)",
    value: 7,
  },
  {
    id: 9,
    capability:
      "Clinical problems not linked to a specific clinical experience group",
  },
  { id: 10, capability: "Ethnicity, culture, diversity, inclusivity" },
  { id: 11, capability: "New presentation of undifferentiated disease" },
  { id: 12, capability: "Prescribing" },
  { id: 13, capability: "Investigation / Results" },
  { id: 14, capability: "Professional conversation / Professional dilemma" },
];

export const NAV_LINKS = [
  {
    name: "Admin",
    link: "/admin",
    icon: HiOutlineShieldCheck,
    key: "admin",
    adminOnly: true,
    scaOnly: false,
  },
  {
    name: "Dashboard",
    link: "/dashboard",
    icon: HiOutlinePresentationChartLine,
    key: "dashboard",
    scaOnly: false,
  },
  {
    name: "AI Practice",
    link: "/mocks",
    icon: RiSpeakLine,
    key: "mocks",
    scaOnly: false,
  },
  {
    name: "A to Z",
    link: "/summary",
    icon: GiSpellBook,
    key: "summary",
    scaOnly: true,
  },
  {
    name: "Contact & Feedback",
    link: "/messages",
    icon: HiOutlineChatBubbleLeftRight,
    key: "messages",
    scaOnly: false,
  },
  {
    name: "Slides",
    link: "/slides",
    icon: HiOutlinePlayCircle,
    key: "slides",
    scaOnly: true,
  },
  {
    name: "Community",
    link: "/community",
    icon: HiOutlineUsers,
    key: "community",
    scaOnly: false,
  },
  {
    name: "Marketplace",
    link: "/marketplace",
    icon: RiUserCommunityFill,
    key: "marketplace",
    scaOnly: true,
    highlight: true,
  },
  {
    name: "Settings",
    link: "/settings",
    icon: HiOutlineCog6Tooth,
    key: "settings",
    scaOnly: false,
  },
  {
    name: "Achievements",
    link: "/achievements",
    icon: LuTrophy,
    key: "achievements",
    scaOnly: false,
  },
];
