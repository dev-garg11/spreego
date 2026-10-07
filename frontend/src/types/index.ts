export * from './user';
export * from './spree';
export * from './open';
export * from './store';
export * from './wallet';

export type ShellTab = 'home' | 'spree' | 'upload' | 'opens' | 'profile';

export interface ConsentState {
  hasAccepted: boolean;
  acceptedAt?: string;
  version: string;
}

export type ModalType = 
  | 'upload'
  | 'challenge_details'
  | 'brand_sponsorship'
  | 'store'
  | 'analytics'
  | 'comment'
  | 'share'
  | null;
