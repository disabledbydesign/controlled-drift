import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { themes } from '@tokens';
import { RoundCheck } from '../RoundCheck';

afterEach(cleanup);

/**
 * Live-verify found the checkbox announcing "mark done" whether or not the task was already
 * done — so a screen reader read a completed task exactly like an open one, with no way to tell
 * them apart. The visual state was correct the whole time; only the announced state was missing.
 *
 * `aria-pressed` on the button that was already there is the fix. It keeps the label as the
 * ACTION ("mark done" — what a click will do) and carries the STATE separately, which is what a
 * toggle button is for. The same attribute is now on all five check sites; this pins the atom
 * they share the grammar with.
 */
describe('a checkbox announces whether it is already done', () => {
  it('is not pressed when the task is open', () => {
    render(<RoundCheck T={themes.celestial} done={false} onClick={() => {}} />);
    expect(screen.getByLabelText('mark done').getAttribute('aria-pressed')).toBe('false');
  });

  it('is pressed when the task is done', () => {
    render(<RoundCheck T={themes.celestial} done={true} onClick={() => {}} />);
    expect(screen.getByLabelText('mark done').getAttribute('aria-pressed')).toBe('true');
  });
});
