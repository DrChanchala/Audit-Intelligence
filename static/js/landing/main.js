/**
 * Landing and authentication page controller.
 */
import { api } from '../shared/api.js';
import { showToast, openModal, closeModal, setupModalDismiss } from '../shared/ui.js';

document.addEventListener('DOMContentLoaded', () => {
  setupModalDismiss();

  const signInForm = document.getElementById('signInForm');
  const signInSubmitBtn = document.getElementById('signInSubmitBtn');
  const openRegisterModalBtn = document.getElementById('openRegisterModalBtn');
  const registerOrgForm = document.getElementById('registerOrgForm');
  const registerSubmitBtn = document.getElementById('registerSubmitBtn');

  // Open Register Organization Modal
  if (openRegisterModalBtn) {
    openRegisterModalBtn.addEventListener('click', () => {
      openModal('registerOrgModal');
    });
  }

  // Handle Sign In Submission
  if (signInForm) {
    signInForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('signInEmail').value.trim();
      const password = document.getElementById('signInPassword').value;

      if (!email || !password) {
        showToast('Please provide both email and password.', 'error');
        return;
      }

      if (signInSubmitBtn) {
        signInSubmitBtn.disabled = true;
        signInSubmitBtn.textContent = 'Authenticating...';
      }

      try {
        const resp = await api.post('/api/auth/login', { email, password });
        showToast('Signed in successfully!', 'success');

        // Check for 'next' parameter in query string
        const urlParams = new URLSearchParams(window.location.search);
        const nextUrl = urlParams.get('next');
        const destination = (nextUrl && nextUrl.startsWith('/') && !nextUrl.startsWith('//'))
          ? nextUrl
          : (resp.home || '/admin');

        window.location.href = destination;
      } catch (err) {
        if (signInSubmitBtn) {
          signInSubmitBtn.disabled = false;
          signInSubmitBtn.textContent = 'Sign In to Workspace';
        }
      }
    });
  }

  // Handle Register Organization Submission
  if (registerOrgForm) {
    registerOrgForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const org_name = document.getElementById('regOrgName').value.trim();
      const industry = document.getElementById('regIndustry').value.trim() || 'Construction & Real Estate';
      const address = document.getElementById('regAddress').value.trim() || undefined;
      const admin_name = document.getElementById('regAdminName').value.trim();
      const admin_phone = document.getElementById('regAdminPhone').value.trim() || undefined;
      const admin_email = document.getElementById('regAdminEmail').value.trim();
      const admin_password = document.getElementById('regAdminPassword').value;

      if (admin_password.length < 10) {
        showToast('Password must be at least 10 characters long.', 'error');
        return;
      }

      if (registerSubmitBtn) {
        registerSubmitBtn.disabled = true;
        registerSubmitBtn.textContent = 'Creating Organization...';
      }

      try {
        const payload = {
          org_name,
          industry,
          address,
          admin_name,
          admin_phone,
          admin_email,
          admin_password,
        };

        const resp = await api.post('/api/auth/register-org-admin', payload);
        showToast(`Organization '${org_name}' created successfully!`, 'success');
        closeModal('registerOrgModal');

        setTimeout(() => {
          window.location.href = resp.home || '/admin';
        }, 300);
      } catch (err) {
        if (registerSubmitBtn) {
          registerSubmitBtn.disabled = false;
          registerSubmitBtn.textContent = 'Create Organization';
        }
      }
    });
  }
});
