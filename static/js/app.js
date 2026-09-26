/* ============================================
   MINISOCIAL — APP.JS (FULLY FIXED v3.0)
   All features: Edit, Delete, Share, Like,
   Save, Comment, Reaction, Follow, Suggestions
   ============================================ */

/* ============ HELPERS ============ */
function getCookie(name) {
  const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return v ? v.pop() : '';
}
const CSRF = getCookie('csrftoken');

function showToast(msg) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  const container = document.getElementById('toast-container');
  if (container) container.appendChild(t);
  else document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

function linkifyHashtagsIn(el) {
  if (!el || el.dataset.linkified) return;
  el.dataset.linkified = '1';
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  const textNodes = [];
  let node;
  while ((node = walker.nextNode())) textNodes.push(node);

  textNodes.forEach(textNode => {
    const text = textNode.nodeValue;
    if (!/#\w+/.test(text)) return;
    const frag = document.createDocumentFragment();
    let lastIndex = 0;
    const regex = /#(\w+)/g;
    let match;
    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        frag.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
      }
      const a = document.createElement('a');
      a.href = `/search/?q=%23${match[1]}`;
      a.textContent = '#' + match[1];
      a.style.color = 'var(--primary)';
      a.style.fontWeight = '600';
      frag.appendChild(a);
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < text.length) {
      frag.appendChild(document.createTextNode(text.slice(lastIndex)));
    }
    if (textNode.parentNode) {
      textNode.parentNode.replaceChild(frag, textNode);
    }
  });
}

/* ============ THEME ============ */
const themeBtn = document.getElementById('theme-toggle');
const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);
if (themeBtn) {
  themeBtn.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
  themeBtn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    themeBtn.textContent = next === 'dark' ? '☀️' : '🌙';
  });
}

/* ============ COMPOSER (postTextarea) ============ */
const postBtn = document.getElementById('post-btn');
const postTextarea = document.getElementById('post-content');
const charCount = document.getElementById('char-count');
const imageInput = document.getElementById('image-input');
const videoInput = document.getElementById('video-input');
const imagePreview = document.getElementById('image-preview');

function updatePostBtn() {
  const hasText = postTextarea?.value.trim().length > 0;
  const hasImage = imageInput?.files[0];
  const hasVideo = videoInput?.files[0];
  if (postBtn) postBtn.disabled = !(hasText || hasImage || hasVideo);
}

if (postTextarea) {
  postTextarea.addEventListener('input', () => {
    if (charCount) charCount.textContent = postTextarea.value.length;
    updatePostBtn();
  });
}

if (imageInput) {
  imageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      if (imagePreview) {
        imagePreview.innerHTML = '';
        const img = document.createElement('img');
        img.src = ev.target.result;
        imagePreview.appendChild(img);
      }
      updatePostBtn();
    };
    reader.readAsDataURL(file);
  });
}

if (videoInput) {
  videoInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > 50) {
      showToast('⚠️ Video too large (max 50MB)');
      videoInput.value = '';
      return;
    }
    showToast(`📹 Video selected (${sizeMB.toFixed(1)}MB)`);
    updatePostBtn();
  });
}

if (postBtn) {
  postBtn.addEventListener('click', async () => {
    const content = postTextarea.value.trim();
    const image = imageInput?.files[0];
    const video = videoInput?.files[0];
    if (!content && !image && !video) return;

    const formData = new FormData();
    if (content) formData.append('content', content);
    if (image) formData.append('image', image);
    if (video) formData.append('video', video);

    postBtn.disabled = true;
    try {
      const res = await fetch('/api/post/', {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF },
        body: formData
      });
      if (res.ok) {
        showToast('Post shared! 🎉');
        setTimeout(() => location.reload(), 400);
      } else {
        showToast('Failed to post');
        postBtn.disabled = false;
      }
    } catch (err) {
      showToast('Network error');
      postBtn.disabled = false;
    }
  });
}

/* ============ EMOJI MAP ============ */
const reactionEmojis = {
  like: '👍',
  love: '❤️',
  haha: '😂',
  wow: '😮',
  sad: '😢',
  angry: '😡',
};

/* ============ POST MENU (EDIT/DELETE) ============ */
document.addEventListener('click', (e) => {
  if (!e.target.closest('.post-menu')) {
    document.querySelectorAll('.menu-dropdown.show').forEach(m => {
      m.classList.remove('show');
    });
  }
});

document.addEventListener('click', (e) => {
  const menuBtn = e.target.closest('.menu-btn');
  if (!menuBtn) return;
  e.preventDefault();
  e.stopPropagation();

  const menu = menuBtn.nextElementSibling;
  if (!menu || !menu.classList.contains('menu-dropdown')) return;

  document.querySelectorAll('.menu-dropdown.show').forEach(m => {
    if (m !== menu) m.classList.remove('show');
  });
  menu.classList.toggle('show');
});

/* ============ EDIT POST ============ */
document.addEventListener('click', async (e) => {
  const editLink = e.target.closest('.edit-post');
  if (!editLink) return;
  e.preventDefault();
  e.stopPropagation();

  const postId = editLink.dataset.postId;
  const postEl = document.querySelector(`.post[data-post-id="${postId}"]`);
  if (!postEl) return;

  const contentEl = postEl.querySelector('.post-content');
  const oldContent = contentEl ? contentEl.textContent : '';
  const newContent = prompt('Edit post:', oldContent);

  if (newContent && newContent.trim() && newContent.trim() !== oldContent) {
    try {
      const res = await fetch(`/api/post/${postId}/edit/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': CSRF,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ content: newContent.trim() })
      });
      if (res.ok) {
        if (contentEl) contentEl.textContent = newContent.trim();
        showToast('Post updated ✏️');
      } else {
        showToast('Failed to update');
      }
    } catch (err) {
      showToast('Network error');
    }
  }
  document.querySelectorAll('.menu-dropdown.show').forEach(m => m.classList.remove('show'));
});

/* ============ DELETE POST ============ */
document.addEventListener('click', async (e) => {
  const deleteLink = e.target.closest('.delete-post');
  if (!deleteLink) return;
  e.preventDefault();
  e.stopPropagation();

  const postId = deleteLink.dataset.postId;
  if (!confirm('Delete this post?')) return;

  try {
    const res = await fetch(`/api/post/${postId}/delete/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF }
    });
    if (res.ok) {
      const postEl = document.querySelector(`.post[data-post-id="${postId}"]`);
      if (postEl) postEl.remove();
      showToast('Post deleted 🗑️');
    } else {
      showToast('Failed to delete');
    }
  } catch (err) {
    showToast('Network error');
  }
  document.querySelectorAll('.menu-dropdown.show').forEach(m => m.classList.remove('show'));
});

/* ============ REACTION PICKER ============ */
document.addEventListener('mouseover', (e) => {
  const wrapper = e.target.closest('.reaction-wrapper');
  if (!wrapper) return;
  const picker = wrapper.querySelector('.reaction-picker');
  if (picker) picker.classList.add('show');
});

document.addEventListener('mouseout', (e) => {
  const wrapper = e.target.closest('.reaction-wrapper');
  if (!wrapper) return;
  const picker = wrapper.querySelector('.reaction-picker');
  if (picker) {
    setTimeout(() => {
      if (!wrapper.matches(':hover')) picker.classList.remove('show');
    }, 200);
  }
});

document.querySelectorAll('.reaction-wrapper').forEach(wrapper => {
  const picker = wrapper.querySelector('.reaction-picker');
  const btn = wrapper.querySelector('.reaction-btn');
  if (!picker || !btn) return;
  let pressTimer;

  btn.addEventListener('touchstart', () => {
    pressTimer = setTimeout(() => picker.classList.add('show'), 300);
  });
  btn.addEventListener('touchend', () => clearTimeout(pressTimer));
  btn.addEventListener('touchmove', () => clearTimeout(pressTimer));
});

document.addEventListener('click', async (e) => {
  const option = e.target.closest('.reaction-option');
  if (!option) return;
  e.preventDefault();
  e.stopPropagation();

  const wrapper = option.closest('.reaction-wrapper');
  const btn = wrapper.querySelector('.reaction-btn');
  const picker = wrapper.querySelector('.reaction-picker');
  const postId = btn.dataset.postId;
  const reaction = option.dataset.reaction;

  try {
    const res = await fetch(`/api/reaction/${postId}/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': CSRF,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({ reaction })
    });

    const data = await res.json();
    if (res.ok) {
      const iconEl = btn.querySelector('.reaction-icon');
      const countEl = btn.querySelector('.reaction-count');
      if (iconEl) iconEl.textContent = data.reaction ? reactionEmojis[data.reaction] : '👍';
      if (countEl) countEl.textContent = Object.values(data.counts || {}).reduce((a, b) => a + b, 0);
      btn.classList.toggle('is-active', !!data.reaction);
      btn.setAttribute('aria-pressed', data.reaction ? 'true' : 'false');
      if (picker) picker.classList.remove('show');
    }
  } catch (err) {
    console.error('Reaction error:', err);
  }
});

document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.reaction-btn');
  if (!btn || e.target.closest('.reaction-option')) return;
  e.preventDefault();

  const postId = btn.dataset.postId;
  try {
    const res = await fetch(`/api/reaction/${postId}/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': CSRF,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({ reaction: 'like' })
    });

    const data = await res.json();
    if (res.ok) {
      const iconEl = btn.querySelector('.reaction-icon');
      const countEl = btn.querySelector('.reaction-count');
      if (iconEl) iconEl.textContent = data.reaction ? reactionEmojis[data.reaction] : '👍';
      if (countEl) countEl.textContent = Object.values(data.counts || {}).reduce((a, b) => a + b, 0);
      btn.classList.toggle('is-active', !!data.reaction);
      btn.setAttribute('aria-pressed', data.reaction ? 'true' : 'false');
    }
  } catch (err) {
    console.error('Like error:', err);
  }
});

/* ============ COMMENT ============ */
document.addEventListener('submit', async (e) => {
  const form = e.target.closest('.comment-form');
  if (!form) return;
  e.preventDefault();
  const input = form.querySelector('input');
  const content = input.value.trim();
  if (!content) return;

  try {
    const res = await fetch(`/api/comment/${form.dataset.postId}/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': CSRF,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({ content })
    });
    const data = await res.json();
    if (res.ok) {
      const div = document.createElement('div');
      div.className = 'comment';
      div.innerHTML = `<strong>${data.author}</strong>${data.content}`;
      form.parentElement.insertBefore(div, form);
      input.value = '';
      showToast('Comment added 💬');
    }
  } catch (err) {
    console.error('Comment error:', err);
  }
});

/* ============ REPLY ============ */
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.reply-btn');
  if (!btn) return;
  const text = prompt('Reply:');
  if (!text || !text.trim()) return;

  try {
    const res = await fetch(`/api/comment/${btn.dataset.postId}/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': CSRF,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        content: text.trim(),
        parent_id: btn.dataset.commentId
      })
    });
    const data = await res.json();
    if (res.ok) {
      const parent = btn.closest('.comment');
      const reply = document.createElement('div');
      reply.className = 'comment reply';
      reply.innerHTML = `<strong>${data.author}</strong>${data.content}`;
      parent.appendChild(reply);
      showToast('Reply added 💬');
    }
  } catch (err) {
    console.error('Reply error:', err);
  }
});

/* ============ FOLLOW ============ */
const followBtn = document.getElementById('follow-btn');
if (followBtn) {
  followBtn.addEventListener('click', async () => {
    try {
      const res = await fetch(`/api/follow/${followBtn.dataset.username}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF }
      });
      const data = await res.json();
      if (res.ok) {
        followBtn.classList.toggle('following', data.following);
        followBtn.textContent = data.following ? 'Following ✓' : 'Follow +';
        const fc = document.getElementById('followers-count');
        if (fc) fc.textContent = data.followers_count;
        showToast(data.following ? 'Now following!' : 'Unfollowed');
      }
    } catch (err) {
      console.error('Follow error:', err);
    }
  });
}

/* ============ SAVE POST ============ */
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.save-btn');
  if (!btn) return;
  e.preventDefault();
  try {
    const res = await fetch(`/api/save/${btn.dataset.postId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF }
    });
    const data = await res.json();
    if (res.ok) {
      btn.classList.toggle('saved', data.saved);
      const icon = btn.querySelector('.reaction-icon');
      const label = btn.querySelector('span:not(.reaction-icon)');
      if (icon) icon.textContent = data.saved ? '🔖' : '📑';
      if (label) label.textContent = data.saved ? 'Saved' : 'Save';
      showToast(data.saved ? 'Post saved 🔖' : 'Removed from saved');
    }
  } catch (err) {
    console.error('Save error:', err);
  }
});

/* ============ HASHTAG LINKIFY ============ */
document.querySelectorAll('.post-content').forEach(linkifyHashtagsIn);

/* ============ INFINITE SCROLL ============ */
let currentPage = 1;
let loadingPosts = false;
let noMorePosts = false;

const feedContainer = document.getElementById('feed');
const loadMoreBtn = document.getElementById('load-more-btn');
const sentinel = document.getElementById('load-more-sentinel');

async function loadMorePosts() {
  if (loadingPosts || noMorePosts || !feedContainer) return;
  loadingPosts = true;
  if (loadMoreBtn) loadMoreBtn.textContent = 'Loading...';

  const nextPage = currentPage + 1;
  try {
    const res = await fetch(`/?page=${nextPage}`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await res.json();

    if (data.html) {
      const temp = document.createElement('div');
      temp.innerHTML = data.html;
      while (temp.firstChild) feedContainer.appendChild(temp.firstChild);
      currentPage = nextPage;
      feedContainer.querySelectorAll('.post-content').forEach(linkifyHashtagsIn);
    }

    if (!data.has_next) {
      noMorePosts = true;
      if (loadMoreBtn) loadMoreBtn.style.display = 'none';
      const end = document.createElement('p');
      end.style.cssText = 'text-align:center;color:var(--text-muted);padding:2rem 1rem;font-size:.95rem;';
      end.textContent = '🎉 You\'re all caught up!';
      feedContainer.appendChild(end);
    } else {
      if (loadMoreBtn) loadMoreBtn.textContent = 'Load More ↓';
    }
  } catch (err) {
    console.error('Failed to load more posts', err);
    if (loadMoreBtn) loadMoreBtn.textContent = 'Retry';
  }
  loadingPosts = false;
}

if (loadMoreBtn) loadMoreBtn.addEventListener('click', loadMorePosts);

if (sentinel && 'IntersectionObserver' in window) {
  const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) loadMorePosts();
  }, { rootMargin: '200px' });
  observer.observe(sentinel);
}

/* ============ SUGGESTIONS ============ */
async function loadRightSidebarSuggestions() {
  const list = document.getElementById('suggestions-list');
  if (!list) return;

  try {
    const res = await fetch('/api/suggestions/');
    const data = await res.json();

    if (!data.users || data.users.length === 0) {
      list.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem;padding:.5rem 1rem;">No suggestions yet</p>';
      return;
    }

    list.innerHTML = '';
    data.users.forEach(u => {
      const item = document.createElement('div');
      item.className = 'suggestion-item';
      item.innerHTML = `
        <a href="/profile/${u.username}/" class="avatar" style="width:38px;height:38px;font-size:.85rem;text-decoration:none;">
          ${u.avatar
            ? `<img src="${u.avatar}" style="width:100%;height:100%;object-fit:cover;">`
            : u.username[0].toUpperCase()
          }
        </a>
        <div class="suggestion-info">
          <strong>${u.username}</strong>
          <small>${u.followers} followers</small>
        </div>
        <button class="suggestion-follow" data-username="${u.username}">Follow</button>
      `;
      list.appendChild(item);
    });
  } catch (e) {
    list.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem;padding:.5rem 1rem;">Failed to load</p>';
  }
}

loadRightSidebarSuggestions();

/* ============ SUGGESTION FOLLOW ============ */
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.suggestion-follow');
  if (!btn || btn.classList.contains('following')) return;

  try {
    const res = await fetch(`/api/follow/${btn.dataset.username}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF }
    });
    const data = await res.json();
    if (res.ok) {
      btn.textContent = 'Following ✓';
      btn.classList.add('following');
      showToast('Now following!');
    }
  } catch (err) {
    console.error('Follow error:', err);
  }
});

/* ============ LIVE NOTIFICATION BELL ============ */
const notifBell = document.getElementById('notif-bell');

if (notifBell) {
  setInterval(async () => {
    try {
      const res = await fetch('/api/unread/');
      const data = await res.json();

      let badge = document.getElementById('notif-badge');
      if (data.count > 0) {
        if (!badge) {
          badge = document.createElement('span');
          badge.id = 'notif-badge';
          badge.className = 'badge';
          notifBell.appendChild(badge);
        }
        badge.textContent = data.count;
      } else if (badge) {
        badge.remove();
      }
    } catch (err) {}
  }, 15000);
}

/* ============ FRIEND REQUESTS ============ */
async function sendFriendRequest(userId) {
  try {
    const res = await fetch(`/friend-request/send/${userId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF, 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await res.json();
    if (data.status === 'sent' || data.status === 'accepted') {
      showToast('✅ Send the Friend Request');
      setTimeout(() => location.reload(), 1200);
    } else {
      showToast('❌ ' + (data.msg || 'Something went wrong'));
    }
  } catch (err) {
    showToast('❌ Network error');
  }
}

async function acceptRequest(reqId) {
  try {
    const res = await fetch(`/friend-request/accept/${reqId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF, 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await res.json();
    if (data.status === 'accepted') {
      showToast('✅ Friend request accepted!');
      setTimeout(() => location.reload(), 1200);
    }
  } catch (err) {
    showToast('❌ Network error');
  }
}

async function rejectRequest(reqId) {
  try {
    const res = await fetch(`/friend-request/reject/${reqId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF, 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await res.json();
    if (data.status === 'rejected') {
      showToast('❌ Friend request rejected');
      setTimeout(() => location.reload(), 1200);
    }
  } catch (err) {
    showToast('❌ Network error');
  }
}

/* ============ POST DRAFTS ============ */
const draftBtn = document.getElementById('draft-btn');

if (draftBtn) {
  draftBtn.addEventListener('click', async () => {
    const content = postTextarea.value.trim();
    const image = imageInput?.files[0];
    const video = videoInput?.files[0];

    if (!content && !image && !video) {
      showToast('⚠️ Nothing to save');
      return;
    }

    const fd = new FormData();
    if (content) fd.append('content', content);
    if (image) fd.append('image', image);
    if (video) fd.append('video', video);

    try {
      const res = await fetch('/api/draft/save/', {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF },
        body: fd
      });
      const data = await res.json();
      if (res.ok) {
        showToast('💾 Draft saved!');
        postTextarea.value = '';
        imagePreview.innerHTML = '';
        if (imageInput) imageInput.value = '';
        if (videoInput) videoInput.value = '';
        updatePostBtn();
      } else {
        showToast('❌ ' + (data.error || 'Failed'));
      }
    } catch (err) {
      showToast('❌ Network error');
    }
  });
}

// Load draft on page load
(async () => {
  if (!postTextarea) return;
  try {
    const res = await fetch('/api/draft/');
    const data = await res.json();
    if (data.draft && data.draft.content) {
      postTextarea.value = data.draft.content;
      if (charCount) charCount.textContent = data.draft.content.length;
      updatePostBtn();

      showToast('📝 Draft loaded from ' + data.draft.updated_at);

      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.className = 'tool-btn';
      delBtn.innerHTML = '🗑️ <span>Discard Draft</span>';
      delBtn.style.cssText = 'background:#fef2f2;color:#ef4444;border-color:#fecaca;';
      delBtn.onclick = async () => {
        if (!confirm('Discard this draft?')) return;
        try {
          const r = await fetch(`/api/draft/${data.draft.id}/delete/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF }
          });
          if (r.ok) {
            postTextarea.value = '';
            if (charCount) charCount.textContent = '0';
            delBtn.remove();
            showToast('🗑️ Draft discarded');
          }
        } catch (e) {}
      };

      const tools = document.querySelector('.composer-tools');
      if (tools) tools.appendChild(delBtn);
    }
  } catch (e) {
    console.error('Failed to load draft', e);
  }
})();

/* ============ TOGGLE POST MENU (legacy) ============ */
function togglePostMenu(event, postId) {
  event.stopPropagation();
  const menu = document.getElementById(`menu-${postId}`);
  if (!menu) return;

  document.querySelectorAll('.menu-dropdown.show').forEach(m => {
    if (m.id !== `menu-${postId}`) m.classList.remove('show');
  });

  menu.classList.toggle('show');
}