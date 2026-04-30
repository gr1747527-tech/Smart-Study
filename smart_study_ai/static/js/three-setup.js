// Three.js 3D Background Setup
let scene, camera, renderer, particles;

function initThreeJS() {
    // Scene setup
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    
    renderer = new THREE.WebGLRenderer({
        canvas: document.getElementById('bg-canvas'),
        alpha: true
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    
    // Create floating particles
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 1000;
    
    const posArray = new Float32Array(particlesCount * 3);
    
    for(let i = 0; i < particlesCount * 3; i++) {
        posArray[i] = (Math.random() - 0.5) * 5;
    }
    
    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    
    const particlesMaterial = new THREE.PointsMaterial({
        size: 0.005,
        color: '#ffffff',
        blending: THREE.AdditiveBlending
    });
    
    particles = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particles);
    
    // Add central geometric shape
    const geometry = new THREE.IcosahedronGeometry(0.5, 0);
    const material = new THREE.MeshBasicMaterial({
        color: '#667eea',
        wireframe: true,
        transparent: true,
        opacity: 0.3
    });
    const icosahedron = new THREE.Mesh(geometry, material);
    scene.add(icosahedron);
    
    camera.position.z = 2;
    
    // Animation loop
    function animate() {
        requestAnimationFrame(animate);
        
        particles.rotation.y += 0.0005;
        particles.rotation.x += 0.0003;
        
        icosahedron.rotation.x += 0.002;
        icosahedron.rotation.y += 0.003;
        
        renderer.render(scene, camera);
    }
    
    animate();
    
    // Handle window resize
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}

function animateResponse() {
    // Special animation when AI responds
    const timeline = gsap.timeline();
    
    timeline.to(particles.material, {
        size: 0.01,
        duration: 0.3,
        yoyo: true,
        repeat: 1
    });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initThreeJS);