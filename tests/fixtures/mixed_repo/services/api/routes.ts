import { validateRequest } from "./validators";

export function handleRoute(req: any) {
  if (!validateRequest(req)) {
    throw new Error("request validation failed");
  }
  return true;
}
