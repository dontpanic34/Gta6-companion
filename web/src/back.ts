/** Pile de gestionnaires « retour » : un panneau ouvert s'enregistre pour être fermé par le bouton retour. */
const stack: (() => boolean)[] = [];
export function onBack(fn: () => boolean) { stack.push(fn); return () => { const i = stack.lastIndexOf(fn); if (i >= 0) stack.splice(i, 1); }; }
export function runBackHandlers(): boolean {
  for (let i = stack.length - 1; i >= 0; i--) if (stack[i]()) return true;
  return false;
}
