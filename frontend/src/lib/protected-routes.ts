// The pages that need a signed-in user. The landing page and /law stay public so that
// anyone can learn what LegalLens is and follow a shared Citation.
const PROTECTED = /^\/(ask|contracts)(\/|$)/;

export const needsSignIn = (pathname: string): boolean => PROTECTED.test(pathname);
