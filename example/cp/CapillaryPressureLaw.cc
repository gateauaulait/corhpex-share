// -*- tab-width: 2; indent-tabs-mode: nil; coding: utf-8-with-signature -*-
//-----------------------------------------------------------------------------
// Copyright 2000-2022 CEA (www.cea.fr) IFPEN (www.ifpenergiesnouvelles.com)
// See the top-level COPYRIGHT file for details.
// SPDX-License-Identifier: Apache-2.0
//-----------------------------------------------------------------------------

/*
 * CapillaryPressureLaw.cc
 *  Lois Physiques
 */

//-----------------------------------------------------------
// Loi de la pression capillaire
// Pc = Pe (Sw)^(-1/lambda)
//-----------------------------------------------------------

#include "CapillaryPressureLaw.h"

//=====================================================

template class CapillaryPressureLaw<float, float>;
template class CapillaryPressureLaw<float, double>;
template class CapillaryPressureLaw<double, double>;

