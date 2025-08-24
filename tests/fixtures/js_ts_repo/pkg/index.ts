import { bar } from './util';
import type { T } from './types';
export function foo() {}
export default function FooDefault() {}
export const arrow = () => {};
const arrow2 = () => {}; export { arrow2 };
@dec
export function decorated<T>(arg: T) { return arg; }
declare function declaredFunc();
function localFunc() {}
