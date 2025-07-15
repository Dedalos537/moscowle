import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class UiEventService {
  setupEventListeners(): void {
    const body = document.body;
    const toggleBtn = document.getElementById('toggle-btn');
    const userBtn = document.getElementById('user-btn');
    const searchBtn = document.getElementById('search-btn');
    const menuBtn = document.getElementById('menu-btn');
    const closeBtn = document.getElementById('close-btn');
    const notifBtn = document.getElementById('notification-btn');
    const backBtn = document.querySelector('.back-btn');

    const profile = document.querySelector('.header .flex .profile') as HTMLElement;
    const search = document.querySelector('.header .flex .search-form') as HTMLElement;
    const sideBar = document.querySelector('.side-bar') as HTMLElement;
    const notifBar = document.querySelector('.notification-bar') as HTMLElement;

    toggleBtn?.addEventListener('click', () => {
      const darkMode = localStorage.getItem('dark-mode');
      if (darkMode === 'disabled') {
        document.body.classList.add('dark');
        localStorage.setItem('dark-mode', 'enabled');
      } else {
        document.body.classList.remove('dark');
        localStorage.setItem('dark-mode', 'disabled');
      }
    });

    userBtn?.addEventListener('click', () => {
      profile?.classList.toggle('active');
      search?.classList.remove('active');
    });

    searchBtn?.addEventListener('click', () => {
      search?.classList.toggle('active');
      profile?.classList.remove('active');
    });

    menuBtn?.addEventListener('click', () => {
      sideBar?.classList.toggle('active');
      body.classList.toggle('active');
    });

    closeBtn?.addEventListener('click', () => {
      sideBar?.classList.remove('active');
      body.classList.remove('active');
    });

    notifBtn?.addEventListener('click', () => {
      notifBar?.classList.toggle('active');
    });

    backBtn?.addEventListener('click', () => {
      notifBar?.classList.remove('active');
    });

    window.onscroll = () => {
      profile?.classList.remove('active');
      search?.classList.remove('active');
      if (window.innerWidth < 1200) {
        sideBar?.classList.remove('active');
        body.classList.remove('active');
      }
    };
  }
}
