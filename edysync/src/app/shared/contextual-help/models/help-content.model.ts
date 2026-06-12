import { UserRole } from '../../../core/models/user';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

export interface HelpContent {
  icon?: IconProp;
  title: string;
  description: string;
  sections: HelpSection[];
  relatedLinks?: HelpLink[];
  tips?: string[];
}

export interface HelpSection {
  icon?: IconProp;
  title: string;
  content: string;
  items?: string[];
}

export interface HelpLink {
  label: string;
  route: string;
  icon?: IconProp;
}

export interface TabHelp {
  tab: string;
  content: HelpContent;
}

export interface PageHelp {
  route: string;
  content: HelpContent;
  tabs?: TabHelp[];
}

export interface RoleHelp {
  role: UserRole;
  pages: PageHelp[];
}
