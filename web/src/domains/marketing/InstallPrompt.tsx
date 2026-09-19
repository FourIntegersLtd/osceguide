'use client'

import { useState, useEffect } from "react"
import { FiDownload, FiX, FiInfo, FiCheckCircle } from "react-icons/fi"
import { MdIosShare, MdInstallDesktop, MdAddBox } from "react-icons/md"
import { HiOutlineDotsHorizontal, HiOutlineDotsVertical } from "react-icons/hi"
import { Button } from "@/foundation/ui"
import { useSession } from "@/foundation/session"
import { needsDashboardOnboarding } from "@/domains/marketing/support/onboardingDismissedStorage"

/**
 * Chrome's install prompt event, which lib.dom does not declare.
 * https://developer.mozilla.org/docs/Web/API/BeforeInstallPromptEvent
 */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>
}

function InstallPrompt() {
  // `appType` was the consumer backend's four-product split; the install
  // prompt only needs to know somebody is signed in.
  const { session } = useSession()
  const user = session?.user ?? null
  const appType: string | null = null
  const [isIOS, setIsIOS] = useState(false)
  const [isAndroid, setIsAndroid] = useState(false)
  const [isStandalone, setIsStandalone] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null)
  const [dismissed, setDismissed] = useState(false)
  const [installError, setInstallError] = useState<string | null>(null)
  const [installSuccess, setInstallSuccess] = useState(false)

  const handleClose = () => {
    setDismissed(true)
    setInstallError(null)
    setInstallSuccess(false)
    localStorage.setItem('installPromptDismissed', 'true')
  }

  useEffect(() => {
    // Check if it's mobile device
    const checkMobile = () => {
      const userAgent = navigator.userAgent.toLowerCase()
      const isMobileDevice = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent)
      const isSmallScreen = window.innerWidth <= 768
      setIsMobile(isMobileDevice || isSmallScreen)
    }

    checkMobile()
    window.addEventListener('resize', checkMobile)

    setIsIOS(
      /iPad|iPhone|iPod/.test(navigator.userAgent) &&
        !(window as Window & { MSStream?: unknown }).MSStream
    )

    setIsAndroid(/android/i.test(navigator.userAgent))

    setIsStandalone(window.matchMedia('(display-mode: standalone)').matches)

    // Check if previously dismissed
    const dismissedState = localStorage.getItem('installPromptDismissed')
    if (dismissedState === 'true') {
      setDismissed(true)
    }

    // Listen for beforeinstallprompt event
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault()
      setDeferredPrompt(e as BeforeInstallPromptEvent)
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)

    // Listen for successful installation
    const handleAppInstalled = () => {
      setInstallSuccess(true)
      setDeferredPrompt(null)
      setTimeout(() => {
        handleClose()
      }, 3000)
    }

    window.addEventListener('appinstalled', handleAppInstalled)

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
      window.removeEventListener('appinstalled', handleAppInstalled)
      window.removeEventListener('resize', checkMobile)
    }
  }, [])

  const handleInstallClick = async () => {
    setInstallError(null)
    setInstallSuccess(false)
    
    if (deferredPrompt) {
      try {
        await deferredPrompt.prompt()
        const { outcome } = await deferredPrompt.userChoice
        
        if (outcome === 'accepted') {
          setInstallSuccess(true)
          setDeferredPrompt(null)
          // Auto-dismiss after showing success message
          setTimeout(() => {
            handleClose()
          }, 3000)
        } else {
          setInstallError('Installation was cancelled. Please use the manual steps below.')
          setDeferredPrompt(null)
        }
      } catch (error) {
        console.error('Error showing install prompt:', error)
        setInstallError('Unable to show install prompt. Please use the manual steps below.')
        setDeferredPrompt(null)
      }
    } else {
      setInstallError('Install prompt not available. Please use the manual steps below.')
    }
  }


  if (
    isStandalone ||
    dismissed ||
    !isMobile ||
    /*
     * The old consumer user object carried `user_id` and an inlined
     * `station_progress` array; the platform's `/me` carries neither — progress
     * is its own endpoint. Passing 0 means "no attempts yet", which is the
     * conservative reading: a brand-new person still gets the onboarding, and
     * somebody mid-course sees the prompt once more rather than never.
     * Tracked in docs/port-gaps.md.
     */
    needsDashboardOnboarding(appType, user?.id, 0)
  ) {
    return null
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 flex w-full justify-center px-2 pointer-events-none sm:px-0 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
      <div className="pointer-events-auto mx-auto mb-2 w-full max-w-sm rounded-t-lg border border-gray-200 bg-white p-4 shadow-lg sm:mb-4 sm:p-4">
        <div className="flex items-start sm:items-center justify-between gap-2 sm:gap-0">
          <div className="flex items-center space-x-2 sm:space-x-3 flex-1 min-w-0">
            <div className="flex-shrink-0">
              <FiDownload className="h-6 w-6 sm:h-8 sm:w-8 text-osce-accent" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm sm:text-base font-medium text-gray-900">Install OSCE Guide</h3>
              <p className="text-xs sm:text-base text-gray-500 mt-0.5">
                {isIOS || isAndroid
                  ? "Follow the steps below to download to your device"
                  : "Get quick access to OSCE Guide on your device"
                }
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 flex-shrink-0">
            {!isIOS && deferredPrompt && (
              <Button
                type="button"
                size="sm"
                onClick={handleInstallClick}
                className="whitespace-nowrap"
              >
                Install
              </Button>
            )}
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 transition-colors p-1 flex-shrink-0"
              aria-label="Close"
            >
              <FiX className="h-5 w-5" />
            </button>
          </div>
        </div>
        {isIOS && (
          <div className="mt-3 sm:mt-3 p-3 sm:p-3 bg-osce-accent-muted rounded-md">
            <div className="text-sm sm:text-base text-osce-accent-hover mb-2 font-medium">
              Using <span className="font-bold">Safari</span>:
            </div>
            <div className="space-y-2 sm:space-y-1.5">
              <div className="flex items-start sm:items-center space-x-2 text-sm sm:text-base text-osce-accent-hover">
                <HiOutlineDotsHorizontal className="h-4 w-4 flex-shrink-0 mt-0.5 sm:mt-0" />
                <span>Tap the <span className="font-semibold">horizontal menu</span> button at the bottom right</span>
              </div>
              <div className="flex items-start sm:items-center space-x-2 text-sm sm:text-base text-osce-accent-hover">
                <MdIosShare className="h-4 w-4 flex-shrink-0 mt-0.5 sm:mt-0" />
                <span>Select <span className="font-semibold">Share</span></span>
              </div>
              <div className="flex items-start sm:items-center space-x-2 text-sm sm:text-base text-osce-accent-hover">
                <MdAddBox className="h-4 w-4 flex-shrink-0 mt-0.5 sm:mt-0" />
                <span>Choose <span className="font-semibold">&quot;Add to Home Screen&quot;</span></span>
              </div>
            </div>
          </div>
        )}
        {isAndroid && !isIOS && (
          <div className="mt-3 sm:mt-3 p-3 sm:p-3 bg-green-50 rounded-md">
            <div className="text-sm sm:text-base text-green-900 mb-2 font-medium">
              Using <span className="font-bold">Chrome</span>:
            </div>
            {installSuccess && (
              <div className="mb-2 p-2 bg-green-100 border border-green-300 rounded text-sm sm:text-base text-green-800 flex items-center gap-2">
                <FiCheckCircle className="h-4 w-4 flex-shrink-0" />
                <span>Installation started! The app will be added to your home screen shortly.</span>
              </div>
            )}
            {installError && (
              <div className="mb-2 p-2 bg-red-100 border border-red-300 rounded text-sm sm:text-base text-red-800">
                {installError}
              </div>
            )}
            {!installSuccess && (
              <div className="space-y-2 sm:space-y-1.5">
                {deferredPrompt ? (
                  <>
                    <div className="flex items-start sm:items-center space-x-2 text-sm sm:text-base text-green-800">
                      <FiDownload className="h-4 w-4 flex-shrink-0 mt-0.5 sm:mt-0" />
                      <span>Tap the <span className="font-semibold">Install</span> button above</span>
                    </div>
                    <div className="text-sm sm:text-base text-green-700 font-medium text-center pt-1 pb-1">
                      OR
                    </div>
                  </>
                ) : null}
                <div className="flex items-start sm:items-center space-x-2 text-sm sm:text-base text-green-800">
                  <HiOutlineDotsVertical className="h-4 w-4 flex-shrink-0 mt-0.5 sm:mt-0" />
                  <span>Tap the <span className="font-semibold">menu</span> button (three vertical dots) in the bottom right</span>
                </div>
                <div className="flex items-start sm:items-center space-x-2 text-sm sm:text-base text-green-800">
                  <MdInstallDesktop className="h-4 w-4 flex-shrink-0 mt-0.5 sm:mt-0" />
                  <span>Look for <span className="font-semibold">&quot;Add to Home screen&quot;</span></span>
                </div>
                <div className="mt-2 pt-2 border-t border-green-200">
                  <div className="flex items-start space-x-2 text-sm sm:text-base text-green-700">
                    <FiInfo className="h-3 w-3 mt-0.5 flex-shrink-0" />
                    <span>
                      If you don&apos;t see the option, try opening the site in an incognito browser tab.
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        {!isIOS && !isAndroid && !deferredPrompt && (
          <div className="mt-3 sm:mt-3 p-3 sm:p-3 bg-yellow-50 rounded-md">
            <div className="flex items-start sm:items-center space-x-2 text-sm sm:text-base text-yellow-800">
              <FiInfo className="h-4 w-4 flex-shrink-0 mt-0.5 sm:mt-0" />
              <span>
                Install prompt not available. Please use your browser&apos;s menu to add this site to your home screen.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default InstallPrompt