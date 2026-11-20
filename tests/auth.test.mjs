import test from 'node:test';
import assert from 'node:assert/strict';
import { accountFromUser, loginDestination, normalizeEmail, validateRegistration } from '../src/features/auth/model.ts';

test('registration validates identity and confirmation', () => {
  assert.equal(normalizeEmail('  Creator@Example.com '), 'creator@example.com');
  assert.doesNotThrow(() => validateRegistration('Test User', 'test@example.com', 'Test12345', 'Test12345'));
  assert.throws(() => validateRegistration(' ', 'test@example.com', 'Test12345', 'Test12345'), /name/);
  assert.throws(() => validateRegistration('Test User', 'bad-email', 'Test12345', 'Test12345'), /email/);
  assert.throws(() => validateRegistration('Test User', 'test@example.com', 'short', 'short'), /password/);
  assert.throws(() => validateRegistration('Test User', 'test@example.com', 'Test12345', 'Different'), /confirmation/);
});

test('account comes from the Supabase user; role is trusted only from app_metadata', () => {
  const base = { id: 'u1', email: 'a@test.local' };
  assert.deepEqual(accountFromUser({ ...base, user_metadata: { name: ' Minh ' } }), { id: 'u1', name: 'Minh', email: 'a@test.local', role: 'creator' });
  assert.equal(accountFromUser(base).name, 'a');
  assert.equal(accountFromUser({ ...base, user_metadata: { role: 'admin' } }).role, 'creator');
  assert.equal(accountFromUser({ ...base, app_metadata: { role: 'admin' } }).role, 'admin');
});

test('login return paths remain internal and role-aware', () => {
  assert.equal(loginDestination('/creator/project/saved', 'creator'), '/creator/project/saved');
  assert.equal(loginDestination('/admin/pkb', 'creator'), '/creator/create');
  assert.equal(loginDestination('/admin/pkb', 'admin'), '/admin/pkb');
  assert.equal(loginDestination('https://evil.example', 'creator'), '/creator/create');
  assert.equal(loginDestination(null, 'admin'), '/admin/users');
});
