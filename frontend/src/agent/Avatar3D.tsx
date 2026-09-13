import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useGLTF, useTexture } from '@react-three/drei'
import * as THREE from 'three'
import { clone as skeletonClone } from 'three/examples/jsm/utils/SkeletonUtils.js'

const SKIN = {
  head: '/avatars/karim/head.jpg',
  body: '/avatars/karim/body.jpg',
  eyes: '/avatars/karim/eyes.jpg',
  top: '/avatars/karim/top.jpg',
  bottom: '/avatars/karim/bottom.jpg',
  shoes: '/avatars/karim/shoes.jpg',
}

export type AvatarVariant = 'head' | 'bust'

type ModelProps = {
  levelRef: React.RefObject<number>
  speaking: boolean
  variant: AvatarVariant
  facing?: number
}

/** Décalage vertical pour cadrer la tête (modèle mesuré : haut = 1,815 m, pieds à y=0). */
const BODY_OFFSET_Y = -1.36

/** Cadrage « tête seule » : visage centré, nez/bouche/mâchoire/cou visibles, rien d'autre. */
const FRAME = { yRatio: 0.90, dist: 0.68, fov: 30 }

function AvatarModel({ levelRef, speaking, variant, facing = 0 }: ModelProps) {
  const { scene } = useGLTF('/avatars/avatarsdk.glb')
  const maps = useTexture(SKIN)
  const group = useRef<THREE.Group>(null)
  const bones = useRef<Record<string, THREE.Object3D>>({})
  const morphTargets = useRef<{ dict: Record<string, number>; influences: number[] }[]>([])
  const { camera } = useThree()
  const [anchor, setAnchor] = useState<number | null>(null)

  const model = useMemo(() => skeletonClone(scene), [scene])

  useEffect(() => {
    const b: Record<string, THREE.Object3D> = {}
    const m: { dict: Record<string, number>; influences: number[] }[] = []
    model.traverse((obj) => {
      const mesh = obj as THREE.Mesh & {
        morphTargetDictionary?: Record<string, number>
        morphTargetInfluences?: number[]
      }
      if (mesh.morphTargetDictionary && mesh.morphTargetInfluences) {
        m.push({ dict: mesh.morphTargetDictionary, influences: mesh.morphTargetInfluences })
      }
      if (obj.name) b[obj.name] = obj
    })
    bones.current = b
    morphTargets.current = m

    // habillage : on remplace les textures par la version retouchée (Karim sombre)
    const swap: Record<string, THREE.Texture> = {
      AvatarHead: maps.head,
      AvatarBody: maps.body,
      AvatarLeftEyeball: maps.eyes,
      AvatarRightEyeball: maps.eyes,
      outfit_top: maps.top,
      outfit_bottom: maps.bottom,
      outfit_shoes: maps.shoes,
    }
    for (const tex of Object.values(swap)) {
      tex.colorSpace = THREE.SRGBColorSpace
      tex.flipY = false // convention glTF
      tex.needsUpdate = true
    }
    model.traverse((obj) => {
      const mesh = obj as THREE.Mesh
      if (!mesh.isMesh) return
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
      for (const mat of mats) {
        const tex = mat && (swap as Record<string, THREE.Texture | undefined>)[mat.name]
        if (tex && 'map' in mat) {
          ;(mat as THREE.MeshStandardMaterial).map = tex
          mat.needsUpdate = true
        }
      }
    })

    // cadrage : tête seule, d'après la hauteur réelle du modèle
    // (on mesure la scène source, détachée, pour ne pas inclure le décalage du groupe)
    const box = new THREE.Box3().setFromObject(scene)
    const top = box.max.y
    if (import.meta.env.DEV) console.debug('[avatar] bounds y', box.min.y.toFixed(3), '->', box.max.y.toFixed(3))
    setAnchor(top * FRAME.yRatio + BODY_OFFSET_Y)
  }, [model, scene, variant, maps])

  // place la caméra pile sur le visage (sinon on regarde le torse / les jambes)
  useEffect(() => {
    if (anchor === null) return
    if (import.meta.env.DEV) console.debug('[avatar] face anchor y =', anchor.toFixed(3))
    camera.position.set(0, anchor, FRAME.dist)
    camera.lookAt(0, anchor, 0)
    camera.updateProjectionMatrix()
  }, [anchor, camera])

  const speakingRef = useRef(speaking)
  useEffect(() => {
    speakingRef.current = speaking
  }, [speaking])

  const mouth = useRef(0)
  const blink = useRef(0)
  const nextBlink = useRef(1.5 + Math.random() * 3)

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime
    const dt = Math.min(delta, 0.05)
    const spk = speakingRef.current
    const amp = spk ? Math.min(1, Math.max(0, levelRef.current ?? 0)) : 0

    const g = group.current
    if (g) {
      g.position.y = BODY_OFFSET_Y + Math.sin(t * 0.8) * 0.006
      g.rotation.y = facing + Math.sin(t * 0.33) * 0.05 + (spk ? Math.sin(t * 1.6) * 0.03 : 0)
      g.rotation.z = Math.sin(t * 0.5) * 0.008
    }

    const setBone = (name: string, rx: number, ry: number, rz: number) => {
      const bone = bones.current[name]
      if (!bone) return
      bone.rotation.x = rx
      bone.rotation.y = ry
      bone.rotation.z = rz
    }
    setBone('Spine1', Math.sin(t * 0.9) * 0.012, 0, 0)
    setBone('Spine2', Math.sin(t * 0.9 + 0.4) * 0.012, 0, 0)
    setBone('Neck', Math.sin(t * 0.7) * 0.02, Math.sin(t * 0.5) * 0.03, 0)
    setBone(
      'Head',
      Math.sin(t * 0.6) * 0.03 + (spk ? Math.sin(t * 2.7) * 0.02 : 0),
      Math.sin(t * 0.45) * 0.06 + (spk ? Math.sin(t * 2.4) * 0.04 : 0),
      Math.sin(t * 0.33) * 0.02,
    )
    const armSwing = spk ? Math.sin(t * 3.1) * 0.06 : Math.sin(t * 0.7) * 0.015
    setBone('LeftArm', 0.04, 0, 0.03 + armSwing)
    setBone('RightArm', 0.04, 0, -0.03 - armSwing)

    // bouche : lissage de l'amplitude audio
    mouth.current += (amp - mouth.current) * Math.min(1, dt * 16)
    const talk = mouth.current

    // clignements
    nextBlink.current -= dt
    if (nextBlink.current <= 0) {
      blink.current = 1
      nextBlink.current = 2.2 + Math.random() * 3.5
    }
    blink.current = Math.max(0, blink.current - dt * 6)
    const bl = blink.current

    for (const { dict, influences } of morphTargets.current) {
      const set = (name: string, value: number) => {
        const i = dict[name]
        if (i !== undefined && i < influences.length) influences[i] = value
      }
      set('jawOpen', talk * 0.85)
      set('mouthOpen', talk * 0.5)
      set('viseme_aa', talk * 0.55)
      set('viseme_O', talk > 0.5 ? (talk - 0.5) * 0.8 : 0)
      set('viseme_E', talk > 0.35 && talk < 0.75 ? (talk - 0.35) * 0.5 : 0)
      set('mouthSmile', 0.12)
      set('mouthSmileLeft', 0.1)
      set('mouthSmileRight', 0.1)
      set('browInnerUp', talk * 0.12)
      set('eyeBlinkLeft', bl)
      set('eyeBlinkRight', bl)
    }
  })

  return (
    <group ref={group} position={[0, BODY_OFFSET_Y, 0]}>
      <primitive object={model} />
    </group>
  )
}

function Lights() {
  return (
    <>
      <ambientLight intensity={0.95} />
      <directionalLight position={[1.6, 2.6, 2.2]} intensity={1.15} color="#fff6e9" />
      <directionalLight position={[-2.2, 1.4, 1.2]} intensity={0.45} color="#cde7ff" />
      <pointLight position={[0, 0.4, 1.4]} intensity={0.35} color="#ffffff" />
    </>
  )
}

type Props = {
  levelRef: React.RefObject<number>
  speaking: boolean
  variant?: AvatarVariant
}

export default function Avatar3D({ levelRef, speaking, variant = 'bust' }: Props) {
  return (
    <Canvas
      dpr={[1, 1.75]}
      gl={{ alpha: true, antialias: true }}
      camera={{ position: [0, 0.27, FRAME.dist], fov: FRAME.fov, near: 0.01, far: 20 }}
      style={{ pointerEvents: 'none' }}
    >
      <Lights />
      <Suspense fallback={null}>
        <AvatarModel levelRef={levelRef} speaking={speaking} variant={variant} />
      </Suspense>
    </Canvas>
  )
}

useGLTF.preload('/avatars/avatarsdk.glb')
